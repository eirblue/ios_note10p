/* File-pointer/task lifetime only. Native DMA/MMIO lifetime remains unproven. */
#if defined(MODULE) || defined(CONFIG_EXYNOS_IMA) || defined(CONFIG_EXYNOS_IMA_MODULE)
#error "v145 requires builtin IVA and explicitly IMA-disabled effective profile"
#endif
#if !defined(CONFIG_SOC_EXYNOS9820) || !defined(CONFIG_EXYNOS_IVA) || !defined(CONFIG_ION_EXYNOS) || !defined(CONFIG_64BIT) || CONFIG_IVA_VER != 30
#error "v145 requires the accepted builtin Exynos9820 IVA30/ION/64-bit profile"
#endif
#include <linux/device.h>
#include <linux/kref.h>
#include <linux/list.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/sched/task.h>

static int n145_native_probe(struct platform_device *pdev);
static int n145_native_remove(struct platform_device *pdev);

enum n145_task_owner {
	N145_NATIVE_OWNED,
	N145_CTX_OWNED,
	N145_TASK_DEFERRED,
	N145_CONSUMED
};

struct n145_binding {
	struct kref refs;
	struct device *dev;
	struct iva_dev_data *native;
	struct list_head registry;
	struct list_head files;
	bool registered;
	bool attached;
	bool closing;
	unsigned long history;
};

struct n145_file {
	struct n145_binding *binding;
	struct iva_proc *native;
	struct task_struct *task;
	struct list_head link;
	enum n145_task_owner task_owner;
	bool quarantined;
};

#define N145_UNSAFE 1UL
#define N145_DETACHED 2UL
#define N145_MMAP_ATTEMPT 4UL
#define N145_MMAP_SUCCESS 8UL
static LIST_HEAD(n145_bindings);
static DEFINE_SPINLOCK(n145_registry_lock);
/* Builtin lifetime: never cleared by close/remove/rebind. No owner witness. */
static unsigned long n145_lifetime_history;

static void n145_history(struct n145_binding *binding, unsigned long flags)
{
	unsigned long irq_flags;

	spin_lock_irqsave(&n145_registry_lock, irq_flags);
	n145_lifetime_history |= flags;
	if (binding)
		binding->history |= flags;
	spin_unlock_irqrestore(&n145_registry_lock, irq_flags);
}

static void n145_binding_free(struct kref *refs)
{
	struct n145_binding *binding = container_of(refs, struct n145_binding, refs);
	struct device *dev = binding->dev;

	kfree(binding);
	put_device(dev);
}

static void n145_binding_put(struct n145_binding *binding)
{
	kref_put(&binding->refs, n145_binding_free);
}

/* Caller owns parent device mutex; registry reference is live while listed. */
static struct n145_binding *n145_binding_get(struct device *dev)
{
	struct n145_binding *binding;
	struct n145_binding *found = NULL;
	unsigned long irq_flags;

	spin_lock_irqsave(&n145_registry_lock, irq_flags);
	list_for_each_entry(binding, &n145_bindings, registry) {
		if (binding->dev == dev) {
			kref_get(&binding->refs);
			found = binding;
			break;
		}
	}
	spin_unlock_irqrestore(&n145_registry_lock, irq_flags);
	return found;
}

static int n145_binding_publish(struct n145_binding *binding)
{
	struct n145_binding *other;
	unsigned long irq_flags;
	int result = 0;

	spin_lock_irqsave(&n145_registry_lock, irq_flags);
	list_for_each_entry(other, &n145_bindings, registry) {
		if (other->dev == binding->dev) {
			result = -EBUSY;
			break;
		}
	}
	if (!result) {
		binding->registered = true;
		list_add(&binding->registry, &n145_bindings);
	}
	spin_unlock_irqrestore(&n145_registry_lock, irq_flags);
	return result;
}

static void n145_binding_unpublish(struct n145_binding *binding)
{
	unsigned long irq_flags;
	bool drop = false;

	spin_lock_irqsave(&n145_registry_lock, irq_flags);
	if (binding->registered) {
		binding->registered = false;
		list_del_init(&binding->registry);
		drop = true;
	}
	spin_unlock_irqrestore(&n145_registry_lock, irq_flags);
	if (drop)
		n145_binding_put(binding);
}

/* No native dereference until exact attached binding is validated. */
static bool n145_file_attached(struct n145_file *ctx)
{
	struct n145_binding *binding = ctx->binding;
	unsigned long irq_flags;
	bool registered;

	spin_lock_irqsave(&n145_registry_lock, irq_flags);
	registered = binding->registered;
	spin_unlock_irqrestore(&n145_registry_lock, irq_flags);
	if (!registered || !binding->attached || binding->closing ||
			!binding->native || ctx->quarantined || !ctx->native)
		return false;
	if (dev_get_drvdata(binding->dev) != binding->native ||
			ctx->native->iva_data != binding->native ||
			ctx->task_owner != N145_NATIVE_OWNED ||
			!ctx->task || ctx->native->tsk != ctx->task) {
		ctx->quarantined = true;
		n145_history(binding, N145_UNSAFE);
		return false;
	}
	return true;
}

static int iva_ctrl_open(struct inode *inode, struct file *filp)
{
	struct miscdevice *misc = filp->private_data;
	struct device *dev = misc->parent;
	struct n145_binding *binding;
	struct n145_file *ctx;
	struct iva_proc *proc = NULL;
	int result;

	(void)inode;
	/* misc_open holds misc_mtx: never wait on remove's parent mutex here. */
	if (!device_trylock(dev))
		return -EBUSY;
	binding = n145_binding_get(dev);
	if (!binding || !binding->attached || binding->closing ||
			binding->native != dev_get_drvdata(dev)) {
		result = -ENODEV;
		goto out_binding;
	}
	ctx = kzalloc(sizeof(*ctx), GFP_KERNEL);
	if (!ctx) {
		result = -ENOMEM;
		goto out_binding;
	}
	result = n145_native_open(binding->native, &proc);
	if (result) {
		kfree(ctx);
		goto out_binding;
	}
	ctx->binding = binding;
	ctx->native = proc;
	ctx->task = proc->tsk;
	ctx->task_owner = N145_NATIVE_OWNED;
	INIT_LIST_HEAD(&ctx->link);
	list_add(&ctx->link, &binding->files);
	filp->private_data = ctx;
	device_unlock(dev);
	return 0;
out_binding:
	device_unlock(dev);
	if (binding)
		n145_binding_put(binding);
	return result;
}

static long iva_ctrl_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
	struct n145_file *ctx = filp->private_data;
	struct n145_binding *binding;
	struct n144_buffer_call call;
	long result;

	if (!ctx)
		return -ENODEV;
	binding = ctx->binding;
	n144_buffer_call_init(&call);
	device_lock(binding->dev);
	if (n145_file_attached(ctx))
		result = n144_iva_ctrl_ioctl_body(ctx->native, cmd, arg, &call);
	else
		result = -ENODEV;
	device_unlock(binding->dev);
	/* May unbind/free every native pointer: only cached result after this. */
	n144_buffer_call_finish(&call);
	return result;
}

static int iva_ctrl_mmap(struct file *filp, struct vm_area_struct *vma)
{
	struct n145_file *ctx = filp->private_data;
	struct n145_binding *binding;
	int result;

	if (!ctx)
		return -ENODEV;
	binding = ctx->binding;
	device_lock(binding->dev);
	n145_history(binding, N145_MMAP_ATTEMPT);
	if (n145_file_attached(ctx)) {
		result = n145_native_mmap(ctx->native, vma);
		if (!result)
			n145_history(binding, N145_MMAP_SUCCESS);
	} else {
		result = -ENODEV;
	}
	device_unlock(binding->dev);
	return result;
}

static int iva_ctrl_release(struct inode *inode, struct file *filp)
{
	struct n145_file *ctx = filp->private_data;
	struct n145_binding *binding;
	struct iva_proc *proc;
	struct task_struct *task = NULL;
	int result = 0;

	(void)inode;
	if (!ctx)
		return 0;
	binding = ctx->binding;
	device_lock(binding->dev);
	if (n145_file_attached(ctx)) {
		proc = ctx->native;
		task = ctx->task;
		ctx->native = NULL;
		ctx->task = NULL;
		ctx->task_owner = N145_TASK_DEFERRED;
		list_del_init(&ctx->link);
		result = n145_native_release(proc);
		ctx->task_owner = N145_CONSUMED;
	} else if (!binding->attached && binding->closing && !ctx->native &&
			!ctx->quarantined && ctx->task_owner == N145_CTX_OWNED && ctx->task) {
		task = ctx->task;
		ctx->task = NULL;
		ctx->task_owner = N145_CONSUMED;
		list_del_init(&ctx->link);
	} else {
		/* Unknown ownership: keep ctx/binding/reference, never guess a put. */
		ctx->quarantined = true;
		n145_history(binding, N145_UNSAFE);
		device_unlock(binding->dev);
		return -EIO;
	}
	filp->private_data = NULL;
	device_unlock(binding->dev);
	if (task)
		put_task_struct(task);
	kfree(ctx);
	n145_binding_put(binding);
	return result;
}

static int iva_ctl_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct n145_binding *binding;
	int result;

	binding = kzalloc(sizeof(*binding), GFP_KERNEL);
	if (!binding)
		return -ENOMEM;
	binding->dev = get_device(dev);
	if (!binding->dev) {
		kfree(binding);
		return -ENODEV;
	}
	kref_init(&binding->refs);
	INIT_LIST_HEAD(&binding->registry);
	INIT_LIST_HEAD(&binding->files);
	result = n145_binding_publish(binding);
	if (result) {
		n145_binding_put(binding);
		return result;
	}
	result = n145_native_probe(pdev);
	if (result) {
		n145_binding_unpublish(binding);
		return result;
	}
	binding->native = platform_get_drvdata(pdev);
	if (binding->native)
		binding->attached = true;
	else
		n145_history(binding, N145_UNSAFE);
	return result;
}

static int iva_ctl_remove(struct platform_device *pdev)
{
	struct n145_binding *binding = n145_binding_get(&pdev->dev);
	struct n145_file *ctx;
	int result;

	/* Driver core already owns device mutex through subsequent devres drain. */
	if (binding) {
		binding->closing = true;
		binding->attached = false;
		binding->native = NULL;
		n145_history(binding, N145_DETACHED);
		list_for_each_entry(ctx, &binding->files, link) {
			ctx->native = NULL;
			if (!ctx->quarantined && ctx->task_owner == N145_NATIVE_OWNED && ctx->task)
				ctx->task_owner = N145_CTX_OWNED;
			else {
				ctx->quarantined = true;
				n145_history(binding, N145_UNSAFE);
			}
		}
	} else {
		n145_history(NULL, N145_UNSAFE);
	}
	result = n145_native_remove(pdev);
	if (binding) {
		n145_binding_unpublish(binding);
		n145_binding_put(binding);
	}
	return result;
}
