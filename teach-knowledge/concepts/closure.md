---
title: "Closure"
kind: concept
created: 2026-08-16
---

# Closure（闭包）

## 定义
一个函数连同其定义时的**词法作用域（lexical scope）**的捆绑。内层函数捕获了外层函数的变量，即使外层函数已经返回，这些变量仍然存活并可被访问。

**面试定义**: "A closure is a function bundled with references to its lexical environment, so it can access outer-scope variables even after the outer function has returned."

## 底层原理
- **Lexical Scoping（词法作用域）**: 变量的可访问性由函数**定义的位置**决定，而非调用位置
- 外层函数返回后，其局部变量不会被垃圾回收，因为闭包仍持有引用（reference）

## 最小示例
```javascript
function counter() {
  let count = 0;           // 被闭包捕获
  return function() {
    return ++count;        // 外层返回后 count 依然活着
  };
}
const c = counter();
c(); // 1
c(); // 2
```

## 典型用途
1. **Data privacy（数据私有）**: 模拟私有变量，外部只能通过暴露的函数访问
2. **Callbacks / Event handlers（回调与事件处理）**: 回调函数记住注册时的环境
3. **Currying / Partial application（柯里化）**: `const add = a => b => a + b`
4. **React Hooks**: stale closure 问题的根源 —— effect/state 捕获的是渲染那一刻的变量快照

## 经典坑
```javascript
// var 只有函数作用域, 三个闭包共享同一个 i
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0); // 3, 3, 3
}
// 修复: 用 let (块级作用域, 每次迭代新绑定)
for (let i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0); // 0, 1, 2
}
```

## Related

- [[Lexical Scope]]
- [[First-class Function]]
- [[Stale Closure]]
- [[Currying]]
