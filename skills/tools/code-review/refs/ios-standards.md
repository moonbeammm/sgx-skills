# iOS Code Review 标准

## 语言识别

当 MR 变更文件包含 `.swift`、`.m`、`.mm`、`.h`、`.storyboard`、`.xib`、`.plist`、`.pbxproj` 时，使用本标准。

---

## 1. 内存管理

### 1.1 循环引用
- [ ] closure/block 中访问 self 必须使用 `[weak self]` 或 `[unowned self]`
- [ ] delegate 属性必须声明为 `weak`
- [ ] Timer / NotificationCenter / KVO 必须在合适时机释放

```swift
// ❌ BAD - 循环引用
service.fetch { result in
    self.data = result  // 强引用 self
}

// ✅ GOOD
service.fetch { [weak self] result in
    guard let self = self else { return }
    self.data = result
}
```

### 1.2 KVO 安全
- [ ] KVO 观察的属性是否会被 UIKit 内部自动修改？
- [ ] 修改被观察属性是否会触发 UIKit 内部 layout？
- [ ] 存储的值在写回时是否仍然合法（frame/contentSize 可能在中途变化）？
- [ ] 使用 `adjustedContentInset` 而非 `contentInset` 计算合法边界

### 1.3 ObjC 内存
- [ ] ObjC 中 block 使用 `@weakify/@strongify` 或 `__weak/__strong`
- [ ] `NSTimer` 必须在 `dealloc` / `viewWillDisappear` 中 `invalidate`

---

## 2. UI 与主线程

### 2.1 主线程操作
- [ ] 所有 UI 操作必须在主线程执行
- [ ] 网络回调、异步操作中更新 UI 必须 `DispatchQueue.main.async`
- [ ] 检查是否有在子线程操作 UIView 的隐患

### 2.2 布局安全
- [ ] `layoutSubviews` 中不要触发新的 layout（避免死循环）
- [ ] `viewDidLayoutSubviews` 中的操作要考虑重复调用
- [ ] Auto Layout 约束冲突检查

### 2.3 转场动画
- [ ] 自定义转场完成后必须调用 `transitionContext.completeTransition()`
- [ ] 转场取消时必须正确恢复视图层级
- [ ] 交互式转场 `interactionControllerFor` 返回 nil 的场景需处理
- [ ] 转场视图的快照在某些场景下可能为空，需防御性检查

---

## 3. 线程安全

### 3.1 数据竞争
- [ ] 多线程访问的属性使用 `@Atomic`、`NSLock`、`DispatchQueue` 保护
- [ ] `UserDefaults` 读写在高并发场景下注意线程安全
- [ ] Core Data 的 `NSManagedObjectContext` 必须在正确的队列上操作

### 3.2 GCD 使用
- [ ] 避免在主队列上 `sync` 调用（死锁）
- [ ] `DispatchWorkItem` cancel 后不要假设 block 一定不会执行
- [ ] `async(after:)` 需考虑对象已释放的场景

---

## 4. Swift 特定

### 4.1 可选值
- [ ] 避免 `force unwrap`（`!`），使用 `guard let` / `if let`
- [ ] `as!` 强转需有充分理由，优先使用 `as?`
- [ ] 数组下标越界检查（`Array.subscript(safe:)` 或先判断 count）

### 4.2 值类型 vs 引用类型
- [ ] 大型 struct 频繁修改考虑 copy-on-write 开销
- [ ] enum associated value 不要持有引用类型（易泄漏）

### 4.3 协议与泛型
- [ ] protocol 中的 `associatedtype` 是否导致类型擦除需求
- [ ] `@objc` protocol 方法不能有默认实现

---

## 5. ObjC 特定

### 5.1 空安全
- [ ] ObjC 方法参数的 `nullable` / `nonnull` 标注
- [ ] `NSArray` / `NSDictionary` 不要插入 nil（crash）
- [ ] `NSAssert` 仅用于调试，Release 下会被移除

### 5.2 Category 冲突
- [ ] Category 方法名添加前缀避免冲突
- [ ] 不要在 Category 中添加属性（用 associated object 除外）

---

## 6. 性能

### 6.1 列表性能
- [ ] `UITableView`/`UICollectionView` cell 复用是否正确
- [ ] `cellForRow` 中避免耗时操作（图片解码、JSON 解析）
- [ ] `estimatedRowHeight` 设置合理值避免卡顿
- [ ] 避免频繁 `reloadData`，优先使用局部刷新

### 6.2 图片处理
- [ ] 大图下采样（`UIGraphicsImageRenderer` / `ImageIO`）
- [ ] 图片缓存策略合理（内存 + 磁盘）
- [ ] 离屏渲染检查（`cornerRadius` + `clipsToBounds` 组合）

### 6.3 动画性能
- [ ] 动画使用 `CATransaction` 或 `UIView.animate`，避免隐式动画
- [ ] `UIGraphicsImageRenderer` 创建快照时注意在后台线程执行
- [ ] 转场动画中避免多余的视图层级创建

---

## 7. 架构规范

### 7.1 依赖管理
- [ ] Bazel BUILD 文件中依赖声明完整
- [ ] `internal import` 用于实现细节，`import` 用于公开接口
- [ ] 避免循环依赖

### 7.2 代码组织
- [ ] 文件头注释中项目名和作者正确
- [ ] MARK 注释合理分隔代码段
- [ ] 开发用的调试代码/临时文件不要提交（TASK.md 等）

### 7.3 Feature Flag
- [ ] 新功能必须有 Feature Flag 保护
- [ ] Feature Flag 命名规范，统一前缀

---

## 8. 安全

- [ ] 敏感数据不写入 `UserDefaults`（使用 Keychain）
- [ ] 网络请求使用 HTTPS
- [ ] URL scheme 处理需验证来源
- [ ] WebView 中 `evaluateJavaScript` 注意 XSS

---

## 9. 重复代码

- [ ] 相同逻辑在多个文件中出现 ≥2 次，应抽取到公共位置
- [ ] Protocol extension / 基类 / 工具方法优先于复制粘贴

# 代码审查

本文用于分支或合并请求（MR）的整体代码质量审查。

## 审查顺序

1. 需求和验收是否实现完整。
2. 改动是否落在正确职责归属。
3. 数据和生命周期时序是否正确。
4. 内存、线程、复用和异步安全。
5. FF、旧路径和线上止损。
6. 日志、埋点、国际化和资源。
7. 编译、测试和验证证据。
8. 代码坏味道和可读性。

## 播放业务重点

- 共享播放器、Story、详情页、小窗是否互相覆盖状态。
- 输入正确后是否被后续职责方重写。
- 列表预加载卡、焦点卡和相邻卡是否使用正确 item。
- 卡片复用是否残留上一个 item 的可见性、约束、图片或订阅。
- 播放状态和全局用户偏好是否被错误等同。
- FF 关闭是否真的走完整线上路径。
- 高频播放回调和滚动路径是否打印日志或执行重操作。

## 问题分级

只报告可操作、由本次变更引入的问题：

- P0/P1：崩溃、数据错乱、播放中断、无法止损。
- P2：确定的行为错误、泄漏、竞态或明显架构扩散。
- P3：值得修复的坏味道，但不阻塞正确性。

结论优先，附紧凑代码位置、触发条件、影响和建议方案。没有问题时明确说明检查过的风险面。
