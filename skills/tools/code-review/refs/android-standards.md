# Android Code Review 标准

## 语言识别

当 MR 变更文件包含 `.kt`、`.java`、`.xml`（Android layout/manifest）、`.gradle`、`.kts` 时，使用本标准。

---

## 1. 内存管理

### 1.1 内存泄漏
- [ ] Activity/Fragment 引用不应被长生命周期对象持有
- [ ] Handler 必须使用 `WeakReference` 或静态内部类
- [ ] 匿名内部类 / lambda 持有外部 Activity 引用时需注意
- [ ] `ViewModel` 中不要持有 Activity/Fragment/View 引用

```kotlin
// ❌ BAD - Handler 持有 Activity 引用
private val handler = Handler(Looper.getMainLooper()) { msg ->
    updateUI()  // 隐式持有 this
    true
}

// ✅ GOOD - WeakReference
private class SafeHandler(activity: MainActivity) : Handler(Looper.getMainLooper()) {
    private val ref = WeakReference(activity)
    override fun handleMessage(msg: Message) {
        ref.get()?.updateUI()
    }
}
```

### 1.2 资源释放
- [ ] `Cursor`、`InputStream`、`TypedArray` 必须 close（使用 `use {}` / `try-with-resources`）
- [ ] `BroadcastReceiver` 必须在合适时机 `unregisterReceiver`
- [ ] `Coroutine` 绑定到正确的 scope（`viewModelScope`/`lifecycleScope`）

---

## 2. 生命周期

### 2.1 Activity/Fragment
- [ ] `onSaveInstanceState` 中保存必要状态
- [ ] `Fragment` 中不要在 `onCreateView` 之前访问 `requireView()`
- [ ] `DialogFragment` 使用 `show()` 时注意 state loss（`commitAllowingStateLoss`）
- [ ] `onDestroy` / `onDestroyView` 中清理资源

### 2.2 LifecycleObserver
- [ ] LiveData 观察使用 `viewLifecycleOwner`（Fragment 中），不要用 `this`
- [ ] Flow 收集使用 `repeatOnLifecycle(Lifecycle.State.STARTED)`

```kotlin
// ❌ BAD - Fragment 中使用 this
viewModel.data.observe(this) { ... }

// ✅ GOOD
viewModel.data.observe(viewLifecycleOwner) { ... }
```

---

## 3. 线程安全

### 3.1 主线程
- [ ] UI 操作必须在主线程
- [ ] `RecyclerView.Adapter.notify*` 必须在主线程调用
- [ ] SharedPreferences 的 `commit()` 在主线程会阻塞，使用 `apply()`

### 3.2 协程
- [ ] IO 操作使用 `Dispatchers.IO`
- [ ] CPU 密集型使用 `Dispatchers.Default`
- [ ] UI 更新使用 `Dispatchers.Main`
- [ ] `GlobalScope` 避免使用，绑定组件生命周期
- [ ] `suspend` 函数中不要阻塞线程（不要在 `withContext(IO)` 中调用 `Thread.sleep`）

### 3.3 并发集合
- [ ] 多线程访问的集合使用 `ConcurrentHashMap` / `Collections.synchronizedList`
- [ ] `StateFlow` / `SharedFlow` 优先于手动加锁

---

## 4. Kotlin 特定

### 4.1 空安全
- [ ] 避免 `!!`（非空断言），使用 `?.`、`?:`、`let`
- [ ] Java 互操作时注意平台类型（`String!`），显式标注可空性
- [ ] `lateinit` 变量在使用前必须确保已初始化（使用 `isInitialized` 检查）

### 4.2 作用域函数
- [ ] `apply`/`also`/`let`/`run`/`with` 使用得当，不要嵌套过深
- [ ] `let` 不要用于简单的 null check + 单行操作（直接 `?.method()` 更清晰）

### 4.3 数据类
- [ ] `data class` 的 `copy()` 注意引用类型字段是浅拷贝
- [ ] `data class` 不要继承（equals/hashCode 行为不一致）

### 4.4 sealed class
- [ ] `when` 表达式处理 sealed class 时必须覆盖所有分支（或使用 `else`）
- [ ] sealed class 用于表示有限状态集，不要滥用

---

## 5. Java 特定

### 5.1 空指针
- [ ] `@Nullable` / `@NonNull` 注解标注参数和返回值
- [ ] 使用 `Objects.requireNonNull()` 做防御性检查
- [ ] `equals()` 方法参数为 null 时必须返回 false

### 5.2 集合
- [ ] `HashMap` 初始容量设置合理（避免频繁 rehash）
- [ ] `Arrays.asList()` 返回的列表不支持 `add/remove`
- [ ] `ConcurrentModificationException`：迭代中不要修改集合

---

## 6. 性能

### 6.1 列表性能
- [ ] `RecyclerView` 使用 `DiffUtil` 代替 `notifyDataSetChanged()`
- [ ] `ViewHolder` 中避免频繁创建对象
- [ ] `RecyclerView.setHasFixedSize(true)` 在适当场景使用
- [ ] 嵌套 `RecyclerView` 设置 `setRecycledViewPool()`

### 6.2 布局优化
- [ ] 布局层级不超过 5 层（使用 `ConstraintLayout` 扁平化）
- [ ] `include` / `merge` / `ViewStub` 合理使用
- [ ] 避免 `layout_weight` 嵌套（双重测量）
- [ ] `overdraw` 检查：移除不必要的背景色

### 6.3 启动优化
- [ ] `Application.onCreate` 中避免耗时初始化
- [ ] 使用 `App Startup` 库延迟初始化
- [ ] `ContentProvider` 数量控制

---

## 7. 架构规范

### 7.1 MVVM
- [ ] View 层不包含业务逻辑
- [ ] ViewModel 不持有 View 引用
- [ ] Repository 层统一数据来源
- [ ] UseCase 单一职责

### 7.2 依赖注入
- [ ] Hilt / Dagger 注入标注正确（`@Inject`、`@Provides`、`@Binds`）
- [ ] Scope 选择正确（`@Singleton`、`@ActivityScoped`、`@ViewModelScoped`）
- [ ] Module 不要过于庞大，按功能拆分

### 7.3 代码组织
- [ ] 包结构清晰（按功能模块划分）
- [ ] 开发调试代码不要提交
- [ ] `BuildConfig` 区分 Debug/Release 行为

---

## 8. 安全

- [ ] 敏感数据使用 `EncryptedSharedPreferences`
- [ ] 网络请求使用 HTTPS，证书校验不要被禁用
- [ ] `WebView` 的 `addJavascriptInterface` 注意安全（`@JavascriptInterface` 标注）
- [ ] `Intent` 数据大小不超过 1MB（TransactionTooLargeException）
- [ ] `exported="true"` 的组件需验证调用方权限

---

## 9. Gradle / 构建

- [ ] 依赖版本统一管理（Version Catalog / buildSrc）
- [ ] 避免使用 `implementation` 暴露传递依赖给使用方
- [ ] `minSdk` / `targetSdk` / `compileSdk` 版本合理
- [ ] ProGuard 规则覆盖新增的反射 / 序列化类

---

## 10. 重复代码

- [ ] 相同逻辑在多个文件中出现 ≥2 次，应抽取到公共位置
- [ ] Extension function / 基类 / 工具类优先于复制粘贴
