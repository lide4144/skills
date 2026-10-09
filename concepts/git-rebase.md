---
title: "Git Rebase"
kind: concept
created: 2026-08-16
---

---
title: "Git Rebase"
kind: concept
created: 2026-08-16
---

# Git Rebase

## 定义
【Rebase（变基）】把一串提交从旧的基点剪下来，重放到新的基点之上，形成一条直线历史。
**面试定义**: "Rebase replays your commits on top of a new base, producing a linear history."

## 为什么 pull 要用 --rebase
多端同时写一个仓库时（比如台式机+笔记本都记笔记），普通 `git pull` 默认走 merge：远端有你本地没有的提交时，会造出一个 merge commit（合并提交），历史变成反复分叉的地铁图。

`git pull --rebase` 的做法是三步：
1. 把你本地**还没推送**的提交临时摘下（放到一边）
2. 快进到远端最新（等价于 git fetch + 移动指针）
3. 把你的提交**逐个重放**到最新基点之上

结果：历史永远是一条直线，你的提交永远叠在最新远端之上，push 必然是 fast-forward，不会产生合并提交。

## 底层抽象
Commit 是不可变对象，rebase 并不是移动提交，而是**逐个重新创建**内容等价、哈希不同的新提交（因为 parent 变了）。这就是为什么 rebase 过的分支需要 force push——它改写了历史。

## 安全边界（trade-off）
- ✅ 安全：rebase **只属于自己的、还没推送给别人的**本地提交。个人知识库场景完全满足。
- ❌ 危险：在共享公共分支上 rebase，别人基于旧哈希的工作会全部悬空。金科玉律：*Never rebase public history.*
- `--autostash`：工作区有未提交改动时，先自动 stash、rebase 完再 pop，避免脏工作区阻塞。

## 对比
| | merge | rebase |
|---|---|---|
| 历史 | 保留分叉真相，有合并提交 | 直线，干净 |
| 哈希 | 不变 | 重写 |
| 冲突解决 | 一次解决 | 每个重放提交都可能要解决 |
| 适用 | 公共分支集成交付 | 本地整理、同步个人仓库 |

## Related

- [[Fast-forward]]
- [[Merge Commit]]
