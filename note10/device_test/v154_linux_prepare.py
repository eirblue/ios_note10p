"""One stock-Linux IVA diagnostic installer; no transfer or reservation overlays."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'note10/device_test'
WORKFLOW = '.github/workflows/note10-v154-linux-iva-diagnostic.yml'
JOB = 'v154-linux-iva-diagnostic'
REPOSITORY = 'eirblue/ios_note10p'
COMMIT = '55f042627bb7030c93550faafa117674d32b21d1'
ARCHIVE_SHA = '46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'
ARCHIVE_BYTES = 212648376
DEFCONFIG = 'exynos9820-d2x_defconfig'
DEFCONFIG_SHA = '0245e51f4e8efa406b329ddc66fa58e0b93f0c84520cf2dd68055e116eacb82b'
IMAGE_LIMIT = 59768832
BOOT_LIMIT = 57671680
CYCLE_MARKER = b'N10_CYCLE_SLOT_UNSET_0123456789A'
BUILD_SCHEMA = 'note10-v154-linux-iva-diagnostic-build-v1'
PACKAGE_SCHEMA = 'note10-v154-linux-iva-diagnostic-package-v1'
PLAN_SCHEMA = 'note10-v154-linux-iva-diagnostic-plan-v1'
INPUTS_SCHEMA = 'note10-v154-linux-package-inputs-v1'
CONTEXT_SCHEMA = 'note10-v154-linux-iva-public-input-v1'
RECIPIENT = 'af9c0ca55448a00faae76c484d05b451443faf46ac94202d75030e170647459d'
PUBLIC_PEM_SHA = '26aa34c6674e8bad6d5e3c1cf9967f33b8b24339fdd2cfd64a92a0ea344e7f51'
NEW_FILES = ('note10/device_test/v154_linux_prepare.py', 'note10/device_test/v154_linux_build.py',
             'note10/device_test/v154_linux_probe.c', 'note10/device_test/v154_linux_return.c',
             'note10/device_test/v154_linux_package.py', 'note10/device_test/v154_linux_cycle.py',
             'note10/device_test/test_v154_linux_diagnostic.py', WORKFLOW)
PARTITIONS = {'boot', 'recovery', 'dtb', 'dtbo', 'vbmeta'}
HOST_SOURCE = {'note10/device_test/v142_iva_native.py': '9497cec3143800a045557d3e2040a1afb0404bc41fa11f9c266a8b14cd269f08', 'note10/device_test/test_v142_iva_native.py': '75def570efce26259ad451840df05e0d3a95eb3d671695e8be49cb47da041286', 'note10/device_test/v143_iva_timer.py': 'cbd29b33ab47b4bd6fb92126a1c09c989767296a5d74329f886143a7e810a06a', 'note10/device_test/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'note10/device_test/test_v143_iva_timer.py': '4f10d8d433f03fd7bdf48bc1f3d159f72171770718977bbe2898db436603b230', 'note10/device_test/v144_iva_buffer.py': 'b444b8f709b66c1f8f207ec1ec35c00372cd5046cb321afc1bcf613ed27d76ae', 'note10/device_test/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'note10/device_test/test_v144_iva_buffer.py': 'cd89349e83320de37a432e8dcea7d70e3218e6e96a4517b64b0faf3c5db753da', 'note10/device_test/v145_iva_sidecar.py': '5792d1626ffc4aa2e00fb44b2332fb704d9451cf9390590e98af7822b03838fe', 'note10/device_test/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377', 'note10/device_test/test_v145_iva_sidecar.py': 'ccd2cc3af61f943df406480a822c742a1cf71d569ccb793220cfb85aa16cde05', 'note10/device_test/v146_iva_user_read.py': '7b1d5e5d3b78e22d18801f5c3eae753ef3abb546de4d146629bb441fae844dc8', 'note10/device_test/test_v146_iva_user_read.py': 'cc52c0d75892de88e171aa8aec2a9673b9c5c86deda00a4f0047597a96b823a6', 'note10/device_test/v147_iva_deinit.py': 'e1155bf25728c651d7b56fae9501057c05a3981d75037f1a8568ac822497fac3', 'note10/device_test/test_v147_iva_deinit.py': 'c459ac049ea36728c4bdcd11568a5446ae977395b28e4531161841be35bc0b9a', 'note10/device_test/v148_iva_init_pm.py': 'f62f03bf16846a2f7d0801558a9223946f85896655a0da6cab807ad86a63ecc0', 'note10/device_test/test_v148_iva_init_pm.py': 'b25e5e2a71b6eebe338585b14efdce5e5e590f9f457343c100bcec3e1944331a', 'note10/device_test/v149_iva_init_state.py': '43573487585fa5cab2926747f0833dff232acfc2efbbe842d98b3414d5abf876', 'note10/device_test/test_v149_iva_init_state.py': 'e7348b501d3b225b2c90a388b4c362118a0927ed2e17a25b66ef6104de7e00e6', 'note10/device_test/v151_iva_mmap_deny.py': '6f0389cae219de419bd501a5e8dd1bfd675b699129870b2b9716ddd894357f0a', 'note10/device_test/test_v151_iva_mmap_deny.py': '16cd375f09e7fc160e3a610fd85bfc5a90b308ec03f66103092b16cfa76b31da', 'note10/device_test/v152_iva_fault_drain.py': 'b79c60b54f8405a1afd90ad68aefbfefd8d11fe92dc614dadd16524e7874235f', 'note10/device_test/test_v152_iva_fault_drain.py': 'dfa73f854bdd9dbbb3c0a019acea69acd960698fa8a9e0c08774c42e8043cc86', 'note10/device_test/v153_iommu_fault_register.py': '66ce02ac452a72d00282cd0bb2a6aa5995e4bd35315dace23cd4d78a248f07cc', 'note10/device_test/test_v153_iommu_fault_register.py': 'b9c30a38ca5edaeb02dbe80eb016ace722a3a3559e5473a352983e9e731e45a3', 'note10/device_test/v150_iva_mbox_register.py': 'b10a752ff612ec64cbc79e5257cde1a7595cba092af7a1ed821bd33e7723e7c2', 'note10/device_test/test_v150_iva_mbox_register.py': 'bbbb548b9e3febe4660c5689ee5692a86b8f1e09b7f8711659d0597ce2ffd9d5'}
TRUSTED = {'note10/device_test/v130_archive.py': 'bc49ffef72f73769de77a55432253f57f14d20433933ac56570f0ebfc3a1bce4', 'note10/device_test/v135_metadata.py': 'd631d04e6f7a4cf1f48e6aeae53be8ef7a48599f4badf08091391fde96e218a9', 'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec'}
STAGE_OUTPUT = {'v142': {'drivers/vision/iva/iva_ctrl.c': 'b13aa35e80c528f2a1d87a4716166a0553cd6bc506974a710bc6ed8678767321', 'drivers/vision/iva/iva_mcu.c': 'ff84d0cc0501169f0864870e250d477e82300ddc82cbeb462e3e9edbcbe206c2'}, 'v143': {'drivers/vision/iva/iva_ctrl.h': 'c7af2d37142cb538cbaa6e94b10b4f38a2391c2d8bd8716238f4ad1e175c4ba6', 'drivers/vision/iva/iva_ipc_queue.c': '97c1f16a8bc298e4950c85bb445683b33d5ffc6352742897c1d4a52e51b284e1', 'drivers/vision/iva/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d'}, 'v144': {'drivers/vision/iva/iva_ctrl.c': 'f7f27fd884e3233bd85a9e23ebcbdb0b677a7bd1baad18cda8c5808e26de2f1b', 'drivers/vision/iva/iva_mem.c': 'c8fba5c0d13a88fae33b3e7e65db8915aa0979b65cd6b10270aceabc774a9231', 'drivers/vision/iva/iva_mem.h': '0b6783f1d557d2499e2452356268f3eaeb5921077939155931118b48c2adffb9', 'drivers/vision/iva/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30'}, 'v145': {'drivers/vision/iva/iva_ctrl.c': '378f40b4deec9dd129f5ce9aebd299bf4ed15159da8327c82e219ab8ce30d6c7', 'drivers/vision/iva/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377'}, 'v146': {'drivers/vision/iva/iva_ctrl.c': 'a2a23d8ee3087b5672b04841ab1bae102221b8c96131dab71498add30d0669a4'}, 'v147': {'drivers/vision/iva/iva_ctrl.c': 'e49a3d744d35fa9f79211ed83e74123e0abdd077f5cd06a8c54801799dc45125'}, 'v148': {'drivers/vision/iva/iva_ctrl.c': 'c557c610a266d545c1cb38519612933208ac02d09f12e4c10b0a9d6b29634e82'}, 'v149': {'drivers/vision/iva/iva_ctrl.c': '8fa6b9138fcfc5113169d818f3eddf6361229daf02c1abf3eb61c00fb53d1ba2'}, 'v151': {'drivers/vision/iva/iva_ctrl.c': 'bd25f242f96501d06e80da563cf4a3ba6dec5a85dd7e886411eeef6637f87562'}, 'v152': {'drivers/iommu/exynos-iommu.c': 'e365f1d2396b816fc6f9d4b56f0065de0c7af28448d171b0e68762c7a68a2487', 'drivers/iommu/exynos-iommu.h': '354205ed662a1f2234b5fdc3c98252a88f3e8aacf972b7243b5f518e46c99096', 'drivers/iommu/exynos-iovmm.c': '47a97ae2dc5e42321b718c133bedb1b1302fd5176f9551acea5a74465ddd0abd', 'include/linux/exynos_iovmm.h': '52fe4927e29316d8392c7cf0fa205fc29897209768765b712508ec735ab010e5', 'drivers/vision/iva/iva_ctrl.c': '47c4c2ba8e83a0134ad533b6ec8dddd8fcca92a7bfa0b798cae4b08b6fb13cab'}, 'v153': {'drivers/iommu/exynos-iommu.c': '50b2e198f6723ca8630bb6f82128dc38ab592dbfc6e57b0b1659325ca45f0831'}, 'v150': {'drivers/vision/iva/iva_mbox.c': '7167cdb91a1e5729b2d4aaef87950a17f7b7a0c91792da7eb0df6dcc8a29e331'}}
HOST_PASS = {'v142': {'result_schema': 'note10-v142-iva-firmware-argument-result-v1', 'result_sha256': '98744b73aa47039a65d78f6d327cfad15a1ff6b48ea506387fa4aa7601c60fea', 'passed': True, 'actual_counters': {'NEW_transform_invocations': 1, 'compiler_invocations': 1, 'fixture_processes': 1, 'old_tests_replayed': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'b13aa35e80c528f2a1d87a4716166a0553cd6bc506974a710bc6ed8678767321', 'drivers/vision/iva/iva_mcu.c': 'ff84d0cc0501169f0864870e250d477e82300ddc82cbeb462e3e9edbcbe206c2'}}, 'v143': {'result_schema': 'note10-v143-native-timer-result-v1', 'result_sha256': 'b46cdf224f5ba8c45decdea87044da3f2a9c6ce3f8e3484ab14bbd21e538fe3a', 'passed': True, 'actual_counters': {'NEW_transform_invocations': 1, 'compiler_invocations': 1, 'fixture_processes': 1, 'old_tests_replayed': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.h': 'c7af2d37142cb538cbaa6e94b10b4f38a2391c2d8bd8716238f4ad1e175c4ba6', 'drivers/vision/iva/iva_ipc_queue.c': '97c1f16a8bc298e4950c85bb445683b33d5ffc6352742897c1d4a52e51b284e1', 'drivers/vision/iva/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d'}}, 'v144': {'result_schema': 'v144-native-ion-host-R2-once-v1', 'result_sha256': '89b2fef2468fa03b114ef034874e5d860ad0b8c36a68b66649c535a96beca7b9', 'passed': True, 'actual_counters': {'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0, 'new_transform_count': 0, 'prior_primary_transform_count': 1, 'prior_negative_transform_count': 3}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'f7f27fd884e3233bd85a9e23ebcbdb0b677a7bd1baad18cda8c5808e26de2f1b', 'drivers/vision/iva/iva_mem.c': 'c8fba5c0d13a88fae33b3e7e65db8915aa0979b65cd6b10270aceabc774a9231', 'drivers/vision/iva/iva_mem.h': '0b6783f1d557d2499e2452356268f3eaeb5921077939155931118b48c2adffb9', 'drivers/vision/iva/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30'}}, 'v145': {'result_schema': 'v145-sidecar-host-R2-once-v1', 'result_sha256': '276e983d4c20712b83672cf8bf95149b04942580ab8a6be67b26bb28053771ec', 'passed': True, 'actual_counters': {'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0, 'new_transform_count': 0, 'prior_primary_transform_count': 1, 'prior_negative_transform_count': 2}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': '378f40b4deec9dd129f5ce9aebd299bf4ed15159da8327c82e219ab8ce30d6c7', 'drivers/vision/iva/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377'}}, 'v146': {'result_schema': 'v146-native-user-read-once-v1', 'result_sha256': '0df9ae3fbae8c26d5f643e7e6ae5a7e9ac6c449bd9ffad9ab539372753ba55ea', 'passed': True, 'actual_counters': {'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0, 'primary_transform_count': 1, 'negative_transform_count': 1}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'a2a23d8ee3087b5672b04841ab1bae102221b8c96131dab71498add30d0669a4'}}, 'v147': {'result_schema': 'v147-native-deinit-errno-once-v1', 'result_sha256': 'efce47af07c7b393cb461aae5e9a0a9413b061a7c12ea7fbd6135b4f25654fd7', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'e49a3d744d35fa9f79211ed83e74123e0abdd077f5cd06a8c54801799dc45125'}}, 'v148': {'result_schema': 'v148-native-init-pm-accounting-once-v1', 'result_sha256': '7655e9b748b1d0eadba7b4e73a70205f236214d7c69428a2878c9c92e269b6ab', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'c557c610a266d545c1cb38519612933208ac02d09f12e4c10b0a9d6b29634e82'}}, 'v149': {'result_schema': 'v149-native-init-state-rollback-once-v1', 'result_sha256': '6089ad6f5cfa9f11e35250696ff6961b8668662caa7bf64433ffff5cc239c50c', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': '8fa6b9138fcfc5113169d818f3eddf6361229daf02c1abf3eb61c00fb53d1ba2'}}, 'v151': {'result_schema': 'v151-native-mmap-deny-once-v1', 'result_sha256': '7cdd22fc05026fb8b510a91e2df5cb568f0105a3144db63a85cbd28f3e7a23e2', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'bd25f242f96501d06e80da563cf4a3ba6dec5a85dd7e886411eeef6637f87562'}}, 'v152': {'result_schema': 'v152-native-fault-token-drain-once-v1', 'result_sha256': '62cab768503edf07aee5c4f5ee4817a307aa3d2e50b2b9ed5b762f9543087e3b', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/iommu/exynos-iommu.c': 'e365f1d2396b816fc6f9d4b56f0065de0c7af28448d171b0e68762c7a68a2487', 'drivers/iommu/exynos-iommu.h': '354205ed662a1f2234b5fdc3c98252a88f3e8aacf972b7243b5f518e46c99096', 'drivers/iommu/exynos-iovmm.c': '47a97ae2dc5e42321b718c133bedb1b1302fd5176f9551acea5a74465ddd0abd', 'include/linux/exynos_iovmm.h': '52fe4927e29316d8392c7cf0fa205fc29897209768765b712508ec735ab010e5', 'drivers/vision/iva/iva_ctrl.c': '47c4c2ba8e83a0134ad533b6ec8dddd8fcca92a7bfa0b798cae4b08b6fb13cab'}}, 'v153': {'result_schema': 'v153-native-fault-registration-once-v1', 'result_sha256': 'b432d82497def2474cc22ab76fe5c965fd4941b76c453b6eb358546ce677cb33', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/iommu/exynos-iommu.c': '50b2e198f6723ca8630bb6f82128dc38ab592dbfc6e57b0b1659325ca45f0831'}}, 'v150': {'result_schema': 'v150-native-mailbox-register-unlock-once-v1', 'result_sha256': '6d38bb486c430495cc2b7532f645dd044debfb73ba2ba196bc1a04d4f51752a4', 'passed': True, 'native_output_sha256': {'drivers/vision/iva/iva_mbox.c': '7167cdb91a1e5729b2d4aaef87950a17f7b7a0c91792da7eb0df6dcc8a29e331'}}}
FINAL_NATIVE = {'drivers/vision/iva/iva_ctrl.c': '47c4c2ba8e83a0134ad533b6ec8dddd8fcca92a7bfa0b798cae4b08b6fb13cab', 'drivers/vision/iva/iva_mcu.c': 'ff84d0cc0501169f0864870e250d477e82300ddc82cbeb462e3e9edbcbe206c2', 'drivers/vision/iva/iva_ctrl.h': 'c7af2d37142cb538cbaa6e94b10b4f38a2391c2d8bd8716238f4ad1e175c4ba6', 'drivers/vision/iva/iva_ipc_queue.c': '97c1f16a8bc298e4950c85bb445683b33d5ffc6352742897c1d4a52e51b284e1', 'drivers/vision/iva/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'drivers/vision/iva/iva_mem.c': 'c8fba5c0d13a88fae33b3e7e65db8915aa0979b65cd6b10270aceabc774a9231', 'drivers/vision/iva/iva_mem.h': '0b6783f1d557d2499e2452356268f3eaeb5921077939155931118b48c2adffb9', 'drivers/vision/iva/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'drivers/vision/iva/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377', 'drivers/iommu/exynos-iommu.c': '50b2e198f6723ca8630bb6f82128dc38ab592dbfc6e57b0b1659325ca45f0831', 'drivers/iommu/exynos-iommu.h': '354205ed662a1f2234b5fdc3c98252a88f3e8aacf972b7243b5f518e46c99096', 'drivers/iommu/exynos-iovmm.c': '47a97ae2dc5e42321b718c133bedb1b1302fd5176f9551acea5a74465ddd0abd', 'include/linux/exynos_iovmm.h': '52fe4927e29316d8392c7cf0fa205fc29897209768765b712508ec735ab010e5', 'drivers/vision/iva/iva_mbox.c': '7167cdb91a1e5729b2d4aaef87950a17f7b7a0c91792da7eb0df6dcc8a29e331'}
REQUIRED_CONFIG = {'ARM64': 'y', '64BIT': 'y', 'SMP': 'y', 'SOC_EXYNOS9820': 'y', 'SOC_EXYNOS9820_EVT0': 'n', 'EXYNOS_IVA': 'y', 'IVA_VER': '30', 'IVA_FPGA': 'n', 'ION_EXYNOS': 'y', 'EXYNOS_IOVMM': 'y', 'EXYNOS_IMA': 'n', 'PM': 'y', 'PM_SLEEP': 'y', 'LTO': 'n', 'LTO_CLANG': 'n', 'LTO_NONE': 'y', 'EXYNOS_IOMMU': 'y', 'IOMMU_API': 'y'}
RETAINED = {'note10/device_test/auto_return.c': '9ec43d3d17f12fe90d2ab36e4712537b7f8275f6f27b6536bbef826f9692037d', 'note10/device_test/builtin_init_route.c': '2fb12577bfd332cd83c3e497aa5930c275983e0f9139d22f53b009b0a9249d74', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hexid(value, size=64):
    if type(value) is not str or re.fullmatch('[0-9a-f]{'+str(size)+'}', value) is None:
        raise ValueError('exact hexadecimal identity required')
    return value


def ordinary(path, bound=2*1024*1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= bound:
        raise ValueError('ordinary bounded input required: '+str(path))
    return path.read_bytes()


def pinned(item, bound=2*1024*1024):
    if type(item) is not dict or set(item) != {'path', 'sha256'}:
        raise ValueError('exact path/hash pair required')
    path = Path(item['path'])
    path = (path if path.is_absolute() else ROOT/path).absolute()
    if path != path.resolve():
        raise ValueError('canonical reviewed input path required')
    raw = ordinary(path, bound)
    if sha(raw) != hexid(item['sha256']):
        raise ValueError('input changed: '+str(path))
    return path, raw


def read(path):
    return json.loads(ordinary(path))


def save(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(row, indent=2, sort_keys=True)+'\n').encode('utf-8'))


def private(path):
    path = Path(path)
    path = (path if path.is_absolute() else ROOT/path).absolute()
    if path != path.resolve() or not path.is_relative_to(ROOT/'note10/private'):
        raise ValueError('canonical private path required')
    return path


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(same(actual[key], value) for key, value in expected.items())
    return actual == expected


def source_pins():
    pins = dict(HOST_SOURCE, **TRUSTED, **RETAINED)
    for name, pin in pins.items():
        if sha(ordinary(ROOT/name)) != hexid(pin):
            raise ValueError('accepted source bytes changed: '+name)
    for name in NEW_FILES:
        pins[name] = sha(ordinary(ROOT/name))
    return pins


def module(name, buffers):
    relative = 'note10/device_test/'+name+'.py'
    raw = buffers[relative]
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(ROOT/relative))
    loaded = importlib.util.module_from_spec(spec)
    loaded.__file__ = str(ROOT/relative)
    sys.modules[name] = loaded
    exec(compile(raw, loaded.__file__, 'exec'), loaded.__dict__)
    return loaded


def load_sources(pins):
    if pins != source_pins():
        raise ValueError('exact final source closure differs')
    return {name: ordinary(ROOT/name) for name in pins}


def compose(cache, buffers, modules=None):
    # v151's function_span import resolves only to the already verified v145.
    names = ('v142_iva_native', 'v143_iva_timer', 'v144_iva_buffer', 'v145_iva_sidecar',
             'v146_iva_user_read', 'v147_iva_deinit', 'v148_iva_init_pm', 'v149_iva_init_state',
             'v150_iva_mbox_register', 'v151_iva_mmap_deny', 'v152_iva_fault_drain',
             'v153_iommu_fault_register')
    modules = modules if modules is not None else {name: module(name, buffers) for name in names}
    stages = {}
    for version, name in zip(range(142, 154), names):
        helper = modules[name]
        if version in (142, 143, 144, 152):
            inputs = {key: cache[key] for key in helper.NATIVE_SHA256}
            if version in (143, 144):
                leaf = 'v143_iva_timer.inc' if version == 143 else 'v144_iva_buffer.h'
                output = helper.patch_native(inputs, buffers['note10/device_test/'+leaf])
            else:
                output = helper.patch_native(inputs)
        elif version == 145:
            output = helper.patch_native(cache['drivers/vision/iva/iva_ctrl.c'],
                                         buffers['note10/device_test/v145_iva_sidecar.inc'])
        else:
            target = ('drivers/vision/iva/iva_mbox.c' if version == 150 else
                      'drivers/iommu/exynos-iommu.c' if version == 153 else
                      'drivers/vision/iva/iva_ctrl.c')
            output = helper.patch_native(cache[target])
        hashes = {key: sha(raw) for key, raw in output.items()}
        if hashes != STAGE_OUTPUT['v'+str(version)]:
            raise ValueError('accepted native stage output differs: '+str(version))
        cache.update(output)
        stages['v'+str(version)] = hashes
    if {name: sha(cache[name]) for name in FINAL_NATIVE} != FINAL_NATIVE:
        raise ValueError('exact final native14 composition differs')
    return {name: cache[name] for name in FINAL_NATIVE}, stages


RESTART_PINS = {
    'kernel/reboot.c': 'ed27858a87e0b7fe098510f03054c034a333874017444de2052af3e691d5b3f8',
    'drivers/samsung/sec_reboot.c': '9c598d65fac6c7be4ba9bcf1d3f6d7d5ec218844c28b97653deabc707190d594',
    'drivers/soc/samsung/exynos-reboot.c': 'be332988d59a77ae616a86bd70ac52ecae6dff94715239b84450a22c02633cf8'}


def route_bytes(raw):
    anchor = b'"id=%s boot=%s cycle=%s route=builtin",'
    end = b'n10_cycle_valid() ? (const char *)n10_cycle : "00000000000000000000000000000000");'
    if raw.count(anchor) != 1 or raw.count(end) != 2:
        raise ValueError('pinned builtin route arm seam differs')
    return raw.replace(anchor, b'"id=%s boot=%s cycle=%s route=builtin arm=%d",', 1).replace(
        end, end[:-2]+b', READ_ONCE(n154_arm_result));', 1)


def guard_bytes(route, raw):
    guarded = route.guard_main(raw)
    declaration = b'extern char *n10_builtin_init_argument(void);'
    argument = b'\targv_init[1] = n10_builtin_init_argument();'
    if guarded.count(declaration) != 1 or guarded.count(argument) != 1:
        raise ValueError('pinned post-SYSTEM_RUNNING builtin guard seam differs')
    guarded = guarded.replace(declaration, declaration+b'\nextern void n154_require_return_armed(void);', 1)
    return guarded.replace(argument, b'\tn154_require_return_armed();\n'+argument, 1)


def firmware_fix(raw):
    old = b'$(call cmd,fwbin,$(patsubst %.gen.S,%,$@))'
    new = b'$(call cmd,fwbin,$(if $(wildcard $(srctree)/$(patsubst %.gen.S,%,$@)),$(srctree)/$(patsubst %.gen.S,%,$@),$(patsubst %.gen.S,%,$@)))'
    if raw.count(old) != 1:
        raise ValueError('stock out-of-tree firmware seam differs')
    return raw.replace(old, new, 1)


def install(source, identity, buffers):
    source = Path(source).resolve()
    hexid(identity, 32)
    route = module('builtin_init_route', buffers)
    for name, pin in dict(route.API_PINS, **RESTART_PINS).items():
        if sha(ordinary(source/name)) != pin:
            raise ValueError('stock boot/restart API changed: '+name)
    stock_names = [name for name in FINAL_NATIVE if not name.endswith(('.inc', 'v144_iva_buffer.h'))]
    native, stages = compose({name: ordinary(source/name) for name in stock_names}, buffers)
    outputs = dict(native)
    outputs.update({
        'init/main.c': guard_bytes(route, ordinary(source/'init/main.c')),
        'firmware/Makefile': firmware_fix(ordinary(source/'firmware/Makefile')),
        'drivers/misc/v154_linux_return.c': buffers['note10/device_test/v154_linux_return.c'],
        'drivers/misc/note10_auto_return.c': buffers['note10/device_test/auto_return.c'],
        'drivers/misc/builtin_init_route.c': route_bytes(buffers['note10/device_test/builtin_init_route.c']),
        'drivers/misc/v154_linux_id.h': ('#define N154_BUILD_ID "'+identity+'"\n').encode(),
    })
    kconfig = ordinary(source/'drivers/misc/Kconfig')
    kbuild = ordinary(source/'drivers/misc/Makefile')
    if b'NOTE10_' in kconfig or b'v154_linux_return' in kbuild:
        raise ValueError('fresh stock diagnostic Kconfig/Kbuild required')
    outputs['drivers/misc/Kconfig'] = kconfig+b'''\nconfig NOTE10_V154_LINUX_DIAGNOSTIC
\tbool "Bounded Linux IVA mmap denial diagnostic"
\tdepends on ARM64 && EXYNOS_IVA && INITRAMFS_FORCE
\tdefault n

config NOTE10_BUILTIN_INIT_ROUTE
\tbool
\tdefault y if NOTE10_V154_LINUX_DIAGNOSTIC
'''
    outputs['drivers/misc/Makefile'] = kbuild+b'\nobj-$(CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC) += v154_linux_return.o\n'
    for name, raw in outputs.items():
        target = source/name
        if not target.resolve().is_relative_to(source) or target.is_symlink():
            raise ValueError('unsafe prepared output')
        if name.startswith('drivers/misc/') and name not in ('drivers/misc/Kconfig', 'drivers/misc/Makefile') and target.exists():
            raise ValueError('test-only extension already exists')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return dict(native_output_sha256=FINAL_NATIVE, overlay_output_sha256=stages,
                installed_sha256={name: sha(raw) for name, raw in outputs.items()},
                internal_kexec_limit=0, XNU_execution_allowed=False, reservations_added=0)
