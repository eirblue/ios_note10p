"""One genuine AArch64 native IVA controller-object build; no kernel/Image execution."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import types

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[2]
ROOT = BASE
HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / 'note10/private'
WORKFLOW = '.github/workflows/note10-v149-native-iva-object.yml'
JOB = 'v149-native-iva-object'
REPOSITORY = 'eirblue/ios_note10p'
SCHEMA = 'note10-v149-native-iva-object-result-v1'
SCOPE = 'native-IVA149-controller-object-incremental-only'
COMMIT = '55f042627bb7030c93550faafa117674d32b21d1'
ARCHIVE_SHA = '46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'
ARCHIVE_BYTES = 212648376
DEFCONFIG = 'exynos9820-d2x_defconfig'
DEFCONFIG_SHA = '0245e51f4e8efa406b329ddc66fa58e0b93f0c84520cf2dd68055e116eacb82b'
RECIPIENT = 'af9c0ca55448a00faae76c484d05b451443faf46ac94202d75030e170647459d'
PUBLIC_PEM_SHA = '26aa34c6674e8bad6d5e3c1cf9967f33b8b24339fdd2cfd64a92a0ea344e7f51'
TRUSTED = {
    'note10/device_test/v130_archive.py': 'bc49ffef72f73769de77a55432253f57f14d20433933ac56570f0ebfc3a1bce4',
    'note10/device_test/v135_metadata.py': 'd631d04e6f7a4cf1f48e6aeae53be8ef7a48599f4badf08091391fde96e218a9',
    'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec',
}
HOST_SOURCE = {'note10/device_test/v142_iva_native.py': '9497cec3143800a045557d3e2040a1afb0404bc41fa11f9c266a8b14cd269f08', 'note10/device_test/test_v142_iva_native.py': '75def570efce26259ad451840df05e0d3a95eb3d671695e8be49cb47da041286', 'note10/device_test/v143_iva_timer.py': 'cbd29b33ab47b4bd6fb92126a1c09c989767296a5d74329f886143a7e810a06a', 'note10/device_test/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'note10/device_test/test_v143_iva_timer.py': '4f10d8d433f03fd7bdf48bc1f3d159f72171770718977bbe2898db436603b230', 'note10/device_test/v144_iva_buffer.py': 'b444b8f709b66c1f8f207ec1ec35c00372cd5046cb321afc1bcf613ed27d76ae', 'note10/device_test/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'note10/device_test/test_v144_iva_buffer.py': 'cd89349e83320de37a432e8dcea7d70e3218e6e96a4517b64b0faf3c5db753da', 'note10/device_test/v145_iva_sidecar.py': '5792d1626ffc4aa2e00fb44b2332fb704d9451cf9390590e98af7822b03838fe', 'note10/device_test/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377', 'note10/device_test/test_v145_iva_sidecar.py': 'ccd2cc3af61f943df406480a822c742a1cf71d569ccb793220cfb85aa16cde05', 'note10/device_test/v146_iva_user_read.py': '7b1d5e5d3b78e22d18801f5c3eae753ef3abb546de4d146629bb441fae844dc8', 'note10/device_test/test_v146_iva_user_read.py': 'cc52c0d75892de88e171aa8aec2a9673b9c5c86deda00a4f0047597a96b823a6', 'note10/device_test/v147_iva_deinit.py': 'e1155bf25728c651d7b56fae9501057c05a3981d75037f1a8568ac822497fac3', 'note10/device_test/test_v147_iva_deinit.py': 'c459ac049ea36728c4bdcd11568a5446ae977395b28e4531161841be35bc0b9a', 'note10/device_test/v148_iva_init_pm.py': 'f62f03bf16846a2f7d0801558a9223946f85896655a0da6cab807ad86a63ecc0', 'note10/device_test/test_v148_iva_init_pm.py': 'b25e5e2a71b6eebe338585b14efdce5e5e590f9f457343c100bcec3e1944331a', 'note10/device_test/v149_iva_init_state.py': '43573487585fa5cab2926747f0833dff232acfc2efbbe842d98b3414d5abf876', 'note10/device_test/test_v149_iva_init_state.py': 'e7348b501d3b225b2c90a388b4c362118a0927ed2e17a25b66ef6104de7e00e6'}
HOST_PASS = {'v142': {'result_schema': 'note10-v142-iva-firmware-argument-result-v1', 'result_sha256': '98744b73aa47039a65d78f6d327cfad15a1ff6b48ea506387fa4aa7601c60fea', 'passed': True, 'actual_counters': {'NEW_transform_invocations': 1, 'compiler_invocations': 1, 'fixture_processes': 1, 'old_tests_replayed': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'b13aa35e80c528f2a1d87a4716166a0553cd6bc506974a710bc6ed8678767321', 'drivers/vision/iva/iva_mcu.c': 'ff84d0cc0501169f0864870e250d477e82300ddc82cbeb462e3e9edbcbe206c2'}}, 'v143': {'result_schema': 'note10-v143-native-timer-result-v1', 'result_sha256': 'b46cdf224f5ba8c45decdea87044da3f2a9c6ce3f8e3484ab14bbd21e538fe3a', 'passed': True, 'actual_counters': {'NEW_transform_invocations': 1, 'compiler_invocations': 1, 'fixture_processes': 1, 'old_tests_replayed': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.h': 'c7af2d37142cb538cbaa6e94b10b4f38a2391c2d8bd8716238f4ad1e175c4ba6', 'drivers/vision/iva/iva_ipc_queue.c': '97c1f16a8bc298e4950c85bb445683b33d5ffc6352742897c1d4a52e51b284e1', 'drivers/vision/iva/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d'}}, 'v144': {'result_schema': 'v144-native-ion-host-R2-once-v1', 'result_sha256': '89b2fef2468fa03b114ef034874e5d860ad0b8c36a68b66649c535a96beca7b9', 'passed': True, 'actual_counters': {'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0, 'new_transform_count': 0, 'prior_primary_transform_count': 1, 'prior_negative_transform_count': 3}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'f7f27fd884e3233bd85a9e23ebcbdb0b677a7bd1baad18cda8c5808e26de2f1b', 'drivers/vision/iva/iva_mem.c': 'c8fba5c0d13a88fae33b3e7e65db8915aa0979b65cd6b10270aceabc774a9231', 'drivers/vision/iva/iva_mem.h': '0b6783f1d557d2499e2452356268f3eaeb5921077939155931118b48c2adffb9', 'drivers/vision/iva/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30'}}, 'v145': {'result_schema': 'v145-sidecar-host-R2-once-v1', 'result_sha256': '276e983d4c20712b83672cf8bf95149b04942580ab8a6be67b26bb28053771ec', 'passed': True, 'actual_counters': {'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0, 'new_transform_count': 0, 'prior_primary_transform_count': 1, 'prior_negative_transform_count': 2}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': '378f40b4deec9dd129f5ce9aebd299bf4ed15159da8327c82e219ab8ce30d6c7', 'drivers/vision/iva/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377'}}, 'v146': {'result_schema': 'v146-native-user-read-once-v1', 'result_sha256': '0df9ae3fbae8c26d5f643e7e6ae5a7e9ac6c449bd9ffad9ab539372753ba55ea', 'passed': True, 'actual_counters': {'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0, 'primary_transform_count': 1, 'negative_transform_count': 1}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'a2a23d8ee3087b5672b04841ab1bae102221b8c96131dab71498add30d0669a4'}}, 'v147': {'result_schema': 'v147-native-deinit-errno-once-v1', 'result_sha256': 'efce47af07c7b393cb461aae5e9a0a9413b061a7c12ea7fbd6135b4f25654fd7', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'e49a3d744d35fa9f79211ed83e74123e0abdd077f5cd06a8c54801799dc45125'}}, 'v148': {'result_schema': 'v148-native-init-pm-accounting-once-v1', 'result_sha256': '7655e9b748b1d0eadba7b4e73a70205f236214d7c69428a2878c9c92e269b6ab', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'c557c610a266d545c1cb38519612933208ac02d09f12e4c10b0a9d6b29634e82'}}, 'v149': {'result_schema': 'v149-native-init-state-rollback-once-v1', 'result_sha256': '6089ad6f5cfa9f11e35250696ff6961b8668662caa7bf64433ffff5cc239c50c', 'passed': True, 'actual_counters': {'primary_transform_count': 1, 'negative_transform_count': 1, 'compiler_count': 1, 'fixture_count': 1, 'old_tests_count': 0}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': '8fa6b9138fcfc5113169d818f3eddf6361229daf02c1abf3eb61c00fb53d1ba2'}}}
STAGE_OUTPUT = {'v142': {'drivers/vision/iva/iva_ctrl.c': 'b13aa35e80c528f2a1d87a4716166a0553cd6bc506974a710bc6ed8678767321', 'drivers/vision/iva/iva_mcu.c': 'ff84d0cc0501169f0864870e250d477e82300ddc82cbeb462e3e9edbcbe206c2'}, 'v143': {'drivers/vision/iva/iva_ctrl.h': 'c7af2d37142cb538cbaa6e94b10b4f38a2391c2d8bd8716238f4ad1e175c4ba6', 'drivers/vision/iva/iva_ipc_queue.c': '97c1f16a8bc298e4950c85bb445683b33d5ffc6352742897c1d4a52e51b284e1', 'drivers/vision/iva/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d'}, 'v144': {'drivers/vision/iva/iva_ctrl.c': 'f7f27fd884e3233bd85a9e23ebcbdb0b677a7bd1baad18cda8c5808e26de2f1b', 'drivers/vision/iva/iva_mem.c': 'c8fba5c0d13a88fae33b3e7e65db8915aa0979b65cd6b10270aceabc774a9231', 'drivers/vision/iva/iva_mem.h': '0b6783f1d557d2499e2452356268f3eaeb5921077939155931118b48c2adffb9', 'drivers/vision/iva/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30'}, 'v145': {'drivers/vision/iva/iva_ctrl.c': '378f40b4deec9dd129f5ce9aebd299bf4ed15159da8327c82e219ab8ce30d6c7', 'drivers/vision/iva/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377'}, 'v146': {'drivers/vision/iva/iva_ctrl.c': 'a2a23d8ee3087b5672b04841ab1bae102221b8c96131dab71498add30d0669a4'}, 'v147': {'drivers/vision/iva/iva_ctrl.c': 'e49a3d744d35fa9f79211ed83e74123e0abdd077f5cd06a8c54801799dc45125'}, 'v148': {'drivers/vision/iva/iva_ctrl.c': 'c557c610a266d545c1cb38519612933208ac02d09f12e4c10b0a9d6b29634e82'}, 'v149': {'drivers/vision/iva/iva_ctrl.c': '8fa6b9138fcfc5113169d818f3eddf6361229daf02c1abf3eb61c00fb53d1ba2'}}
FINAL_NATIVE = {'drivers/vision/iva/iva_ctrl.c': '8fa6b9138fcfc5113169d818f3eddf6361229daf02c1abf3eb61c00fb53d1ba2', 'drivers/vision/iva/iva_mcu.c': 'ff84d0cc0501169f0864870e250d477e82300ddc82cbeb462e3e9edbcbe206c2', 'drivers/vision/iva/iva_ctrl.h': 'c7af2d37142cb538cbaa6e94b10b4f38a2391c2d8bd8716238f4ad1e175c4ba6', 'drivers/vision/iva/iva_ipc_queue.c': '97c1f16a8bc298e4950c85bb445683b33d5ffc6352742897c1d4a52e51b284e1', 'drivers/vision/iva/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'drivers/vision/iva/iva_mem.c': 'c8fba5c0d13a88fae33b3e7e65db8915aa0979b65cd6b10270aceabc774a9231', 'drivers/vision/iva/iva_mem.h': '0b6783f1d557d2499e2452356268f3eaeb5921077939155931118b48c2adffb9', 'drivers/vision/iva/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'drivers/vision/iva/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377'}
TARGETS = ('drivers/vision/iva/iva_ctrl.o',)
PREDECESSOR_SOURCE = {'.github/workflows/note10-v148-native-iva-object.yml': '9c008b2ab2e3b77a6bfb1066afdc807f731b711170d8cc93a0e3548a3aa3274b', 'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec', 'note10/device_test/test_v142_iva_native.py': '75def570efce26259ad451840df05e0d3a95eb3d671695e8be49cb47da041286', 'note10/device_test/test_v143_iva_timer.py': '4f10d8d433f03fd7bdf48bc1f3d159f72171770718977bbe2898db436603b230', 'note10/device_test/test_v144_iva_buffer.py': 'cd89349e83320de37a432e8dcea7d70e3218e6e96a4517b64b0faf3c5db753da', 'note10/device_test/test_v145_iva_sidecar.py': 'ccd2cc3af61f943df406480a822c742a1cf71d569ccb793220cfb85aa16cde05', 'note10/device_test/test_v146_iva_user_read.py': 'cc52c0d75892de88e171aa8aec2a9673b9c5c86deda00a4f0047597a96b823a6', 'note10/device_test/test_v147_iva_deinit.py': 'c459ac049ea36728c4bdcd11568a5446ae977395b28e4531161841be35bc0b9a', 'note10/device_test/test_v148_iva_init_pm.py': 'b25e5e2a71b6eebe338585b14efdce5e5e590f9f457343c100bcec3e1944331a', 'note10/device_test/v130_archive.py': 'bc49ffef72f73769de77a55432253f57f14d20433933ac56570f0ebfc3a1bce4', 'note10/device_test/v135_metadata.py': 'd631d04e6f7a4cf1f48e6aeae53be8ef7a48599f4badf08091391fde96e218a9', 'note10/device_test/v142_iva_native.py': '9497cec3143800a045557d3e2040a1afb0404bc41fa11f9c266a8b14cd269f08', 'note10/device_test/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'note10/device_test/v143_iva_timer.py': 'cbd29b33ab47b4bd6fb92126a1c09c989767296a5d74329f886143a7e810a06a', 'note10/device_test/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'note10/device_test/v144_iva_buffer.py': 'b444b8f709b66c1f8f207ec1ec35c00372cd5046cb321afc1bcf613ed27d76ae', 'note10/device_test/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377', 'note10/device_test/v145_iva_sidecar.py': '5792d1626ffc4aa2e00fb44b2332fb704d9451cf9390590e98af7822b03838fe', 'note10/device_test/v146_iva_user_read.py': '7b1d5e5d3b78e22d18801f5c3eae753ef3abb546de4d146629bb441fae844dc8', 'note10/device_test/v147_iva_deinit.py': 'e1155bf25728c651d7b56fae9501057c05a3981d75037f1a8568ac822497fac3', 'note10/device_test/v148_iva_init_pm.py': 'f62f03bf16846a2f7d0801558a9223946f85896655a0da6cab807ad86a63ecc0', 'note10/device_test/v148_object_build.py': 'ca0a6902d3aa3a7a4120646f456bbdbeee11b98ecd26b74f8a69e90f193f557a'}
PREDECESSOR_NATIVE = {'drivers/vision/iva/iva_ctrl.c': 'c557c610a266d545c1cb38519612933208ac02d09f12e4c10b0a9d6b29634e82', 'drivers/vision/iva/iva_ctrl.h': 'c7af2d37142cb538cbaa6e94b10b4f38a2391c2d8bd8716238f4ad1e175c4ba6', 'drivers/vision/iva/iva_ipc_queue.c': '97c1f16a8bc298e4950c85bb445683b33d5ffc6352742897c1d4a52e51b284e1', 'drivers/vision/iva/iva_mcu.c': 'ff84d0cc0501169f0864870e250d477e82300ddc82cbeb462e3e9edbcbe206c2', 'drivers/vision/iva/iva_mem.c': 'c8fba5c0d13a88fae33b3e7e65db8915aa0979b65cd6b10270aceabc774a9231', 'drivers/vision/iva/iva_mem.h': '0b6783f1d557d2499e2452356268f3eaeb5921077939155931118b48c2adffb9', 'drivers/vision/iva/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'drivers/vision/iva/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'drivers/vision/iva/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377'}
PREDECESSOR_PASS = {'schema': 'note10-v148-authenticated-producer-PASS-for-v149-v1', 'passed': True, 'source_head': '6ef0f3992f2a709039e1d4b642a5157d941b0db0', 'run_id': 42473621760, 'run_attempt': 1, 'job_id': 128709954360, 'artifact_id': 13614692029, 'producer_result_sha256': '34405d95eae73b1ef4e38b2018c1b329a9acbb3476780171b4650e5cfc176b70', 'receive_terminal_sha256': '0525d4e68c2aed96575db711f555d6a5c8deb6953e391cf318fbbc8d06cd015b', 'source_sha256': {'.github/workflows/note10-v148-native-iva-object.yml': '9c008b2ab2e3b77a6bfb1066afdc807f731b711170d8cc93a0e3548a3aa3274b', 'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec', 'note10/device_test/test_v142_iva_native.py': '75def570efce26259ad451840df05e0d3a95eb3d671695e8be49cb47da041286', 'note10/device_test/test_v143_iva_timer.py': '4f10d8d433f03fd7bdf48bc1f3d159f72171770718977bbe2898db436603b230', 'note10/device_test/test_v144_iva_buffer.py': 'cd89349e83320de37a432e8dcea7d70e3218e6e96a4517b64b0faf3c5db753da', 'note10/device_test/test_v145_iva_sidecar.py': 'ccd2cc3af61f943df406480a822c742a1cf71d569ccb793220cfb85aa16cde05', 'note10/device_test/test_v146_iva_user_read.py': 'cc52c0d75892de88e171aa8aec2a9673b9c5c86deda00a4f0047597a96b823a6', 'note10/device_test/test_v147_iva_deinit.py': 'c459ac049ea36728c4bdcd11568a5446ae977395b28e4531161841be35bc0b9a', 'note10/device_test/test_v148_iva_init_pm.py': 'b25e5e2a71b6eebe338585b14efdce5e5e590f9f457343c100bcec3e1944331a', 'note10/device_test/v130_archive.py': 'bc49ffef72f73769de77a55432253f57f14d20433933ac56570f0ebfc3a1bce4', 'note10/device_test/v135_metadata.py': 'd631d04e6f7a4cf1f48e6aeae53be8ef7a48599f4badf08091391fde96e218a9', 'note10/device_test/v142_iva_native.py': '9497cec3143800a045557d3e2040a1afb0404bc41fa11f9c266a8b14cd269f08', 'note10/device_test/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'note10/device_test/v143_iva_timer.py': 'cbd29b33ab47b4bd6fb92126a1c09c989767296a5d74329f886143a7e810a06a', 'note10/device_test/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'note10/device_test/v144_iva_buffer.py': 'b444b8f709b66c1f8f207ec1ec35c00372cd5046cb321afc1bcf613ed27d76ae', 'note10/device_test/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377', 'note10/device_test/v145_iva_sidecar.py': '5792d1626ffc4aa2e00fb44b2332fb704d9451cf9390590e98af7822b03838fe', 'note10/device_test/v146_iva_user_read.py': '7b1d5e5d3b78e22d18801f5c3eae753ef3abb546de4d146629bb441fae844dc8', 'note10/device_test/v147_iva_deinit.py': 'e1155bf25728c651d7b56fae9501057c05a3981d75037f1a8568ac822497fac3', 'note10/device_test/v148_iva_init_pm.py': 'f62f03bf16846a2f7d0801558a9223946f85896655a0da6cab807ad86a63ecc0', 'note10/device_test/v148_object_build.py': 'ca0a6902d3aa3a7a4120646f456bbdbeee11b98ecd26b74f8a69e90f193f557a'}, 'native_output_sha256': {'drivers/vision/iva/iva_ctrl.c': 'c557c610a266d545c1cb38519612933208ac02d09f12e4c10b0a9d6b29634e82', 'drivers/vision/iva/iva_ctrl.h': 'c7af2d37142cb538cbaa6e94b10b4f38a2391c2d8bd8716238f4ad1e175c4ba6', 'drivers/vision/iva/iva_ipc_queue.c': '97c1f16a8bc298e4950c85bb445683b33d5ffc6352742897c1d4a52e51b284e1', 'drivers/vision/iva/iva_mcu.c': 'ff84d0cc0501169f0864870e250d477e82300ddc82cbeb462e3e9edbcbe206c2', 'drivers/vision/iva/iva_mem.c': 'c8fba5c0d13a88fae33b3e7e65db8915aa0979b65cd6b10270aceabc774a9231', 'drivers/vision/iva/iva_mem.h': '0b6783f1d557d2499e2452356268f3eaeb5921077939155931118b48c2adffb9', 'drivers/vision/iva/v143_iva_timer.inc': '730e2ab31cada507b7dd380d0a928aae502829b70b86a471d5b4010f626fb24d', 'drivers/vision/iva/v144_iva_buffer.h': 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30', 'drivers/vision/iva/v145_iva_sidecar.inc': '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377'}, 'effective_profile': {'64BIT': 'y', 'ARM64': 'y', 'EXYNOS_IMA': 'n', 'EXYNOS_IOVMM': 'y', 'EXYNOS_IVA': 'y', 'ION_EXYNOS': 'y', 'IVA_FPGA': 'n', 'IVA_VER': '30', 'LTO': 'n', 'LTO_CLANG': 'n', 'LTO_NONE': 'y', 'PM': 'y', 'PM_SLEEP': 'y', 'SMP': 'y', 'SOC_EXYNOS9820': 'y', 'SOC_EXYNOS9820_EVT0': 'n'}, 'effective_profile_evidence': {'EXYNOS_IMA': {'config_state': 'absent-in-generated-config', 'generated_macros_undefined': True, 'production_fence_compiled': True, 'resolved': True}}, 'physical_ready': False, 'owner_success_emitted': False, 'producer_result_schema': 'note10-v148-native-iva-object-result-v1', 'object_sha256': {'drivers/vision/iva/iva_ctrl.o': 'c70b1a4ef1494077a541a9194c45f99e05d5e32f2e5c8a546b289fc9c0f8d767'}}
REQUIRED_CONFIG = {
    'ARM64': 'y', '64BIT': 'y', 'SMP': 'y', 'SOC_EXYNOS9820': 'y', 'SOC_EXYNOS9820_EVT0': 'n',
    'EXYNOS_IVA': 'y', 'IVA_VER': '30', 'IVA_FPGA': 'n', 'ION_EXYNOS': 'y',
    'EXYNOS_IOVMM': 'y', 'EXYNOS_IMA': 'n', 'PM': 'y', 'PM_SLEEP': 'y', 'LTO': 'n', 'LTO_CLANG': 'n', 'LTO_NONE': 'y',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hexid(value, length=64):
    if type(value) is not str or re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is None:
        raise ValueError('exact hexadecimal identity required')
    return value


def ordinary(path, bound):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= bound:
        raise ValueError('ordinary bounded input required: ' + str(path))
    return path.read_bytes()


def module_from_bytes(name, path, raw):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def exact_value(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(exact_value(actual[k], v) for k, v in expected.items())
    return actual == expected


def validated_context(encoded):
    codec_path = ROOT / 'note10/device_test/v135_metadata.py'
    codec_raw = ordinary(codec_path, 2 * 1024 * 1024)
    if sha(codec_raw) != TRUSTED[codec_path.relative_to(ROOT).as_posix()]:
        raise ValueError('original public metadata codec differs')
    codec = module_from_bytes('v149_reviewed_public_codec', codec_path, codec_raw)
    context = codec.decode_public(encoded)
    keys = {'schema', 'scope', 'passed', 'host_pass', 'host_source_sha256', 'orchestration_sha256', 'kernel', 'predecessor148'}
    if (type(context) is not dict or set(context) != keys or
            context['schema'] != 'note10-v149-native-object-public-input-v1' or
            context['scope'] != SCOPE or context['passed'] is not True or
            not exact_value(context['host_pass'], HOST_PASS) or
            not exact_value(context['host_source_sha256'], HOST_SOURCE)):
        raise ValueError('exact carried142..149 actual host PASS/public19 source context required')
    kernel = dict(commit=COMMIT, archive_sha256=ARCHIVE_SHA, defconfig_sha256=DEFCONFIG_SHA)
    if not exact_value(context['kernel'], kernel):
        raise ValueError('exact native public kernel/stock profile binding required')
    orchestration = context['orchestration_sha256']
    if (type(orchestration) is not dict or
            set(orchestration) != set(TRUSTED) | {'note10/device_test/v149_object_build.py', WORKFLOW} or
            any(orchestration.get(name) != pin for name, pin in TRUSTED.items())):
        raise ValueError('separate exact original3 plus new148 orchestration2 pins required')
    pins = dict(HOST_SOURCE, **orchestration)
    buffers = {'note10/device_test/v135_metadata.py': codec_raw}
    for name, pin in pins.items():
        hexid(pin)
        raw = buffers.get(name)
        if raw is None:
            raw = ordinary(ROOT / name, 2 * 1024 * 1024)
            if sha(raw) != pin:
                raise ValueError('reviewed source bytes differ: ' + name)
        buffers[name] = raw
    predecessor148(context['predecessor148'])
    return context, pins, buffers


def predecessor148(row):
    if not exact_value(row, PREDECESSOR_PASS):
        raise ValueError('exact actual authenticated148 predecessor PASS required')


def recipient():
    encoded = os.environ.get('N10_RECIPIENT_PUBLIC_KEY_B64', '')
    if len(encoded) > 8192:
        raise ValueError('bounded original PUBLIC recipient required')
    pem = base64.b64decode(encoded, validate=True)
    if (sha(pem) != PUBLIC_PEM_SHA or b'PRIVATE KEY' in pem or
            not pem.startswith(b'-----BEGIN PUBLIC KEY-----\n') or not pem.endswith(b'-----END PUBLIC KEY-----\n')):
        raise ValueError('original PUBLIC PEM required')
    der = base64.b64decode(b''.join(pem.splitlines()[1:-1]), validate=True)
    if sha(der) != RECIPIENT:
        raise ValueError('original public recipient SPKI required')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--expected-source-head', required=True)
    parser.add_argument('--passed-new-test-context', required=True)
    args = parser.parse_args()
    head = hexid(args.expected_source_head, 40)
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out = out.absolute()
    work = out.with_name(out.name + '-workspace')
    archive = out.with_name(out.name + '-kernel-input.tar.gz')
    if (not sys.platform.startswith('linux') or args.jobs != 4 or out.resolve() != out or
            not out.is_relative_to(PRIVATE) or out == PRIVATE or
            any(path.exists() or path.is_symlink() for path in (out, work, archive))):
        parser.error('one fresh canonical Linux-only private object build required')
    context_keys = ('GITHUB_SHA', 'GITHUB_WORKFLOW_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
                    'GITHUB_REPOSITORY', 'GITHUB_JOB', 'GITHUB_WORKFLOW_REF')
    ci = {key: os.environ.get(key, '') for key in context_keys}
    if (ci['GITHUB_SHA'] != head or ci['GITHUB_WORKFLOW_SHA'] != head or
            re.fullmatch('[1-9][0-9]*', ci['GITHUB_RUN_ID']) is None or ci['GITHUB_RUN_ATTEMPT'] != '1' or
            ci['GITHUB_REPOSITORY'] != REPOSITORY or ci['GITHUB_JOB'] != JOB or
            ci['GITHUB_WORKFLOW_REF'] != REPOSITORY + '/' + WORKFLOW + '@refs/heads/main'):
        parser.error('actual reviewed source/head/job/attempt1 workflow identity required')
    public, source_pins, buffers = validated_context(args.passed_new_test_context)
    recipient()
    modules = {}
    for name in ('v130_archive', 'v142_iva_native', 'v143_iva_timer', 'v144_iva_buffer', 'v145_iva_sidecar', 'v146_iva_user_read', 'v147_iva_deinit', 'v148_iva_init_pm', 'v149_iva_init_state'):
        path = HERE / (name + '.py')
        modules[name] = module_from_bytes('v149_reviewed_' + name, path, buffers[path.relative_to(ROOT).as_posix()])
    archive_module = modules['v130_archive']
    if (archive_module.COMMIT, archive_module.ARCHIVE_SHA, archive_module.DEFCONFIG) != (COMMIT, ARCHIVE_SHA, DEFCONFIG):
        raise ValueError('original source acquisition helper constants differ')
    identity = sha(json.dumps(dict(source=source_pins, ci=ci), sort_keys=True, separators=(',', ':')).encode())[:32]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(mode=0o700)
    result = dict(schema=SCHEMA, version='v149', scope=SCOPE, passed=False, ci_context=ci,
                  producer_argv=[sys.executable, *sys.argv], producer_cwd=str(ROOT),
                  source_sha256=source_pins, build_evidence_id=identity, public_input=public,
                  predecessor148=public['predecessor148'],
                  kernel_commit=COMMIT, kernel_archive_sha256=ARCHIVE_SHA,
                  recipient_sha256=RECIPIENT, targets=list(TARGETS), stages={}, object_evidence={},
                  native_include_compile_status='pending', native_link_validation_status='not-requested',
                  old_tests_replayed=0, host_tests_replayed=0, retained_render_invocations=0,
                  Image_builds=0, hardware_package_emitted=False, physical_ready=False,
                  device_operations=[], owner_success_emitted=False, XNU_execution_allowed=False)
    commands = []
    def save(path, row):
        path.write_bytes((json.dumps(row, indent=2, sort_keys=True) + '\n').encode())
    def persist():
        save(out / 'result.json', result)
    def run(command, label, timeout, allow_failure=False):
        row = dict(argv=[str(item) for item in command], completed=False, label=label)
        commands.append(row)
        save(out / 'commands.json', commands)
        with (out / (label + '.log')).open('xb') as stream:
            done = subprocess.run(row['argv'], cwd=ROOT, env=dict(os.environ, PLATFORM_VERSION='11', ANDROID_MAJOR_VERSION='r'),
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        row.update(completed=True, returncode=done.returncode)
        save(out / 'commands.json', commands)
        if done.returncode and not allow_failure:
            raise ValueError('native build command failed: ' + label)
        return done.returncode
    persist()
    try:
        tools = {}
        for name in ('clang-14', 'gcc', 'make', 'aarch64-linux-gnu-gcc', 'arm-linux-gnueabi-gcc'):
            found = shutil.which(name)
            if not found:
                raise ValueError('required native build tool unavailable: ' + name)
            path = Path(found).resolve()
            tools[name] = dict(path=str(path), sha256=sha(ordinary(path, 512 * 1024 * 1024)),
                               version_argv=[str(path), '--version'], status='version-probe-started')
            save(out / 'toolchain.json', tools)
            version = subprocess.run([str(path), '--version'], capture_output=True, text=True, timeout=30)
            tools[name].update(version=version.stdout[:4096], stderr=version.stderr[:4096],
                               returncode=version.returncode, status='version-probe-completed')
            save(out / 'toolchain.json', tools)
            if version.returncode or (name == 'clang-14' and re.search(r'\bversion 14\.', version.stdout) is None):
                raise ValueError('required actual tool version unavailable: ' + name)
        save(out / 'toolchain.json', tools)
        result['stages']['source_acquire'] = dict(attempts=1, status='started')
        persist()
        archive_module.acquire(archive)
        if archive.stat().st_size != ARCHIVE_BYTES or sha(ordinary(archive, ARCHIVE_BYTES)) != ARCHIVE_SHA:
            raise ValueError('exact fresh public kernel archive differs')
        result['stages']['source_acquire']['status'] = 'completed'
        work.mkdir(mode=0o700)
        result['stages']['source_extract'] = dict(attempts=1, status='started')
        persist()
        source = archive_module.extract(archive, work / 'source')
        objects = work / 'objects'
        objects.mkdir(mode=0o700)
        stock_profile = ordinary(source / 'arch/arm64/configs' / DEFCONFIG, 2 * 1024 * 1024)
        if sha(stock_profile) != DEFCONFIG_SHA:
            raise ValueError('exact stock d2x source profile differs')
        result['stages']['source_extract']['status'] = 'completed'
        native_names = (
            'drivers/vision/iva/iva_ctrl.c', 'drivers/vision/iva/iva_mcu.c',
            'drivers/vision/iva/iva_ctrl.h', 'drivers/vision/iva/iva_ipc_queue.c',
            'drivers/vision/iva/iva_mem.c', 'drivers/vision/iva/iva_mem.h')
        cache = {name: ordinary(source / name, 2 * 1024 * 1024) for name in native_names}
        result['overlay_output_sha256'] = {}
        for version, module_name in ((142, 'v142_iva_native'), (143, 'v143_iva_timer'),
                                     (144, 'v144_iva_buffer'), (145, 'v145_iva_sidecar'),
                                     (146, 'v146_iva_user_read'), (147, 'v147_iva_deinit'), (148, 'v148_iva_init_pm'), (149, 'v149_iva_init_state')):
            module = modules[module_name]
            result['stages']['overlay' + str(version)] = dict(attempts=1, status='started')
            persist()
            if version in (142, 143, 144):
                native_input = {name: cache[name] for name in module.NATIVE_SHA256}
                if version == 142:
                    output = module.patch_native(native_input)
                else:
                    leaf = 'v143_iva_timer.inc' if version == 143 else 'v144_iva_buffer.h'
                    output = module.patch_native(native_input, buffers['note10/device_test/' + leaf])
            elif version == 145:
                output = module.patch_native(cache['drivers/vision/iva/iva_ctrl.c'],
                                             buffers['note10/device_test/v145_iva_sidecar.inc'])
            else:
                output = module.patch_native(cache['drivers/vision/iva/iva_ctrl.c'])
            expected = STAGE_OUTPUT['v' + str(version)]
            hashes = {name: sha(raw) for name, raw in output.items()}
            if hashes != expected:
                raise ValueError('intrinsic native overlay differs from actual host output pins')
            cache.update(output)
            result['overlay_output_sha256']['v' + str(version)] = hashes
            result['stages']['overlay' + str(version)]['status'] = 'completed'
        for name in FINAL_NATIVE:
            path = source / name
            if not path.resolve().is_relative_to(source) or path.is_symlink():
                raise ValueError('unsafe native overlay output path')
            if name.endswith(('.inc', 'v144_iva_buffer.h')) and path.exists():
                raise ValueError('new native helper already exists')
            raw = cache[name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            snapshot = out / 'native-source' / name
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(raw)
        result['native_output_sha256'] = dict(FINAL_NATIVE)
        make = [tools['make']['path'], '-C', str(source), 'O=' + str(objects), 'ARCH=arm64', 'CC=clang-14',
                'CROSS_COMPILE=aarch64-linux-gnu-', 'CLANG_TRIPLE=aarch64-linux-gnu-',
                'CROSS_COMPILE_ARM32=arm-linux-gnueabi-', 'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
                'HOSTCC=gcc', 'HOSTCFLAGS=-Wno-error=deprecated-declarations', 'KCFLAGS=-gdwarf-4']
        result['stages']['defconfig'] = dict(attempts=1, status='started')
        persist()
        run([*make, DEFCONFIG], '01-stock-defconfig', 600)
        config_raw = ordinary(objects / '.config', 2 * 1024 * 1024)
        configuration = {}
        for line in config_raw.decode('utf-8').splitlines():
            if line.startswith('CONFIG_') and '=' in line:
                name, value = line[7:].split('=', 1)
                if name in configuration:
                    raise ValueError('duplicate generated config key')
                configuration[name] = value
            elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
                name = line[9:-11]
                if name in configuration:
                    raise ValueError('duplicate generated config key')
                configuration[name] = 'n'
        effective = {name: configuration.get(name, 'n') for name in REQUIRED_CONFIG if name != 'EXYNOS_IMA'}
        required_without_ima = {name: value for name, value in REQUIRED_CONFIG.items() if name != 'EXYNOS_IMA'}
        if effective != required_without_ima or configuration.get('EXYNOS_IMA') not in (None, 'n'):
            raise ValueError('actual stock native IVA branch differs; no forced profile change')
        ima_state = 'explicit-not-set' if configuration.get('EXYNOS_IMA') == 'n' else 'absent-in-generated-config'
        (out / 'actual-effective.config').write_bytes(config_raw)
        result.update(effective_config_sha256=sha(config_raw), effective_profile=effective,
                      effective_profile_evidence=dict(EXYNOS_IMA=dict(config_state=ima_state, resolved=False)),
                      effective_optional_profile={name: configuration.get(name, 'n') for name in ('MODULES', 'LTO_NONE', 'FTRACE_MCOUNT_RECORD')})
        result['stages']['defconfig']['status'] = 'completed'
        result['stages']['native_object_make'] = dict(attempts=1, status='started')
        persist()
        native_status = run([*make, '-k', 'V=1', '-j' + str(args.jobs), *TARGETS],
                            '02-native-one-object', 1800, allow_failure=True)
        result['native_object_make_exit_code'] = native_status
        persist()
        dependencies = {'iva_ctrl.o': ('v145_iva_sidecar.inc', 'v144_iva_buffer.h', 'iva_mem.h', 'iva_ctrl.h', 'linux/kref.h')}
        for target in TARGETS:
            path = objects / target
            if native_status and (not path.is_file() or not path.stat().st_size):
                continue
            raw = ordinary(path, 64 * 1024 * 1024)
            target_elf = (len(raw) >= 20 and raw[:6] == b'\x7fELF\x02\x01' and
                          int.from_bytes(raw[16:18], 'little') == 1 and int.from_bytes(raw[18:20], 'little') == 183)
            saved = out / 'objects' / target
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(raw)
            row = dict(bytes=len(raw), sha256=sha(raw), artifact_path=str(saved.relative_to(out)),
                       AArch64_ELF64_little_relocatable=target_elf, diagnostic_only=True,
                       command_path=None, command_sha256=None, helper_dependencies={})
            result['object_evidence'][target] = row
            persist()
            cmd_path = path.with_name('.' + path.name + '.cmd')
            cmd_raw = ordinary(cmd_path, 2 * 1024 * 1024) if not native_status or (cmd_path.is_file() and cmd_path.stat().st_size) else b''
            if cmd_raw:
                saved.with_name(cmd_path.name).write_bytes(cmd_raw)
                row.update(command_path=str(saved.with_name(cmd_path.name).relative_to(out)), command_sha256=sha(cmd_raw))
            row['helper_dependencies'] = {name: name.encode() in cmd_raw for name in dependencies[path.name]}
            persist()
            if not native_status and (not target_elf or b'clang-14' not in cmd_raw or
                    re.search(rb'(?:^|\s)-DMODULE(?:\s|=|$)', cmd_raw) is not None or
                    not all(row['helper_dependencies'].values())):
                raise ValueError('actual builtin ELF64 AArch64 clang/native helper evidence required')
            row['diagnostic_only'] = bool(native_status)
        autoconf_path = objects / 'include/generated/autoconf.h'
        if autoconf_path.is_file():
            autoconf = ordinary(autoconf_path, 2 * 1024 * 1024)
            (out / 'generated-autoconf.h').write_bytes(autoconf)
            result['generated_autoconf_sha256'] = sha(autoconf)
            ima_defined = re.search(rb'^\s*#\s*define\s+CONFIG_EXYNOS_IMA(?:_MODULE)?\b', autoconf, re.M) is not None
            result['effective_profile_evidence']['EXYNOS_IMA'].update(
                generated_macros_undefined=not ima_defined, production_fence_compiled=not native_status,
                resolved=not ima_defined and not native_status)
            if ima_defined:
                raise ValueError('generated IMA enabled; sidecar profile forbidden, no override/retry')
        else:
            raise ValueError('actual generated autoconf proof absent')
        if native_status:
            raise ValueError('native object make failed; partial new objects preserved diagnostically')
        if set(result['object_evidence']) != set(TARGETS):
            raise ValueError('exact one controller target evidence required')
        result['effective_profile']['EXYNOS_IMA'] = 'n'
        if result['effective_profile'] != REQUIRED_CONFIG:
            raise ValueError('actual effective profile proof incomplete')
        result['stages']['native_object_make']['status'] = 'completed'
        result.update(passed=True, native_include_compile_status='compiled-by-this-CI')
        persist()
        print(json.dumps(dict(passed=True, native_objects=1, physical_ready=False)))
    except Exception as error:
        for evidence in result['object_evidence'].values():
            evidence['diagnostic_only'] = True
        result.update(status='failed-spent-no-retry', error=str(error)[:512])
        persist()
        raise


if __name__ == '__main__':
    main()
