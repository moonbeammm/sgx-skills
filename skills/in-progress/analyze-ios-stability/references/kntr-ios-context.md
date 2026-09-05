# KNTR iOS Repository Context

Use this reference to choose scope and commands. Verify paths and target names in the current checkout because the monorepo evolves.

## Code surfaces

- `binary/application/*/ios/`: iOS app and extension entry points, resources, generated-Xcode inputs, and app-specific Swift/Objective-C.
- `srcs/**/src/iosMain/`: iOS-specific Kotlin, Swift, and Objective-C interop.
- `srcs/**/src/nativeMain/`: shared native code used by iOS and other native platforms.
- `srcs/**/src/commonMain/`: shared production logic that also runs on iOS.
- `srcs/legacy-loktar/`, `srcs/app-epoch/`, `srcs/base-epoch/`, and `srcs/common-epoch/`: legacy or wrapper layers that can participate in the same iOS call chain.
- `srcs/cc-wrapper/` and native library trees: C/C++ ownership and ABI boundaries.
- `srcs/base/ijk/`: player/native stack; inspect embedded upstream code only when the change or runtime evidence reaches it.
- `binary/application/pdd/ios/` and module preview targets: useful for focused reproduction when the affected module is preview-enabled.

Do not assume an Xcode project is the source of truth. Read the nearest `BUILD.bazel` and Bazel macro inputs. Generated `.xcodeproj` files, Bazel output trees, IDE indexes, dependencies, fixtures, and vendored code are not first-pass audit targets.

The repository also contains large tracked upstream trees. Default-exclude directories named `Vendors`, `Venders`, `ThirdParty`, `External`, and multimedia third-party sources. Re-enter them when a stack, trace, local fork, or current change points there.

## Scope strategy

Prefer this order:

1. Incident frames or user-named module.
2. Current change set and its direct callers/dependents.
3. App lifecycle, bridge, and infrastructure boundaries touched by that path.
4. A bounded high-risk sample for a proactive app audit.

Treat app extensions separately from the host app: they have different lifecycle, memory budget, process, and entry points.

## Repository discovery without rg

```bash
git status --short
git diff --name-only --diff-filter=ACMR
git ls-files '<scope>/*.swift' '<scope>/*.m' '<scope>/*.mm' '<scope>/*.kt'
find <scope> -name BUILD.bazel -print
grep -RInE '<symbol-or-api>' <scope> --include='*.swift' --include='*.m' --include='*.mm' --include='*.h' --include='*.kt'
```

Use `git ls-files` or the bundled scanner for broad inventories so ignored build products do not dominate results. Quote globs and tolerate empty results.

## Architecture checks

- Put shared behavior in `commonMain`; use `iosMain` only for platform APIs or interop.
- Keep `srcs/base/<name>/api` separate from implementations. App/common consumers must depend on `-api`, never `-impl`.
- Gripper 2.0 is preferred. Hilt supports only `SingletonComponent`; lifecycle assumptions from Android component scopes do not transfer to iOS.
- Check initialization idempotency and teardown symmetry for singleton producers, module setup, app delegates, preview shells, and UIKit/Compose bridges.
- Treat `commonMain` coroutines as iOS concurrency code. Verify dispatcher choice, cancellation propagation, and Swift callback/continuation behavior.
- Verify ownership explicitly for `StableRef`, `CPointer`, `COpaquePointer`, Core Foundation create/copy APIs, ObjC blocks, Swift closures, and UIKit/Compose controller/view bridges.

## Existing diagnostics and prevention

Check for reusable instrumentation before adding another mechanism:

- `srcs/legacy-loktar/debug/MLeaksFinder` and `FBRetainCycleDetector`: leak/retain-cycle debugging.
- `srcs/legacy-loktar/common/BFCBlockMonitor` and `BBHitchesMonitor`: blocking/hitch diagnostics.
- `srcs/legacy-loktar/common/BFCFoom`: memory/OOM diagnostics.
- `srcs/legacy-loktar/base/BFC/APM/BFCAnalytics` and `srcs/legacy-loktar/debug/BBCArgus`: runtime evidence and diagnostics.
- `tools/bllint-rules`: existing Kotlin cancellation and blocking/resource checks.
- `tools/bazellint/check_no_ios_reverse_legacy_dep.py`: reverse legacy-dependency validation.

The iOS Bazel configuration already enables strict C/Objective-C warnings, including several ARC, initialization, super-call, and availability checks. Treat compiler success as a useful guard, not proof of runtime safety. Do not assume a uniform sanitizer or Instruments automation entry point exists; verify the actual target configuration first.

## Validation commands

Derive exact labels from the nearest `BUILD.bazel`.

```bash
./bazel-wrapper build //<module>:<library> --config=ios-sim-arm64 --experimental_convenience_symlinks=clean
./bazel-wrapper test //<module>:<test>_ios --config=ios-sim-arm64 --experimental_convenience_symlinks=clean
./ktlint '<module>/**/*.kt' '!srcs/**/build/**' --baseline=.ktlint-baseline.xml
```

Use public `kt_unit_test` and `kt_ui_test` target shapes, not generated internal test targets. For full iOS apps, use the repository make shortcuts only when full-app validation is proportional:

```bash
make iphone
make iphone_b
make ipad2
make biliLink
make bilistudio_ios
```

Do not run a full app build merely to validate a local ownership or parser change if a focused target exists.

## Existing automated signals

- Run scoped ktlint for Kotlin edits.
- Inspect existing bllint coverage before proposing a new custom rule. The repository already checks some cancellation and blocking Compose-resource patterns.
- Treat lint as prevention, not incident proof. Confirm semantic reachability and runtime behavior.
