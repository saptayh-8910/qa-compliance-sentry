# Algorithm learning track

This repository connects interview fundamentals to features in the QA and AI
quality roadmap. Each problem is implemented independently, tested with Pytest,
and then reused in a practical component.

## Stage 1 foundation lab

### Two Sum

- Reference: [LeetCode 1](https://leetcode.com/problems/two-sum/)
- QA connection: find two measurements, prices, or durations that reconcile to
  a target total.
- Simple approach: compare every pair, which costs O(n²) time.
- Implemented approach: store each visited value in a hash map and look for the
  required complement. This costs O(n) time and O(n) space.
- Project decision: return `None` when no pair exists instead of assuming the
  input always contains exactly one solution.

Questions to practice explaining:

1. Why must the lookup happen before storing the current value?
2. How does the approach handle two equal values such as `[3, 3]`?
3. What contract should production code use when no pair exists?

### Contains Duplicate

- Reference: [LeetCode 217](https://leetcode.com/problems/contains-duplicate/)
- QA connection: detect repeated test-case or external record identifiers.
- Simple approach: compare every pair or sort the input first.
- Implemented approach: add identifiers to a set and stop at the first repeat.
  This gives O(n) expected time and O(n) space and supports streamed iterables.
- Production boundary: database uniqueness constraints are stronger when IDs
  are stored persistently or written concurrently.

Questions to practice explaining:

1. Why is a set appropriate when counts are not needed?
2. What are the time and memory tradeoffs versus sorting?
3. Why is application-level checking insufficient for concurrent DB writes?

### Binary Search

- Reference: [LeetCode 704](https://leetcode.com/problems/binary-search/)
- QA connection: locate a known test or bug ID in a sorted collection.
- Simple approach: scan from the beginning in O(n) time.
- Implemented approach: repeatedly discard half the remaining search range,
  giving O(log n) time and O(1) additional space.
- Production decision: sorted input is a documented precondition. Checking the
  order inside the function would itself cost O(n) and remove the key benefit.

Questions to practice explaining:

1. What loop invariant do `left` and `right` maintain?
2. Why does the loop use `left <= right`?
3. What can go wrong if the collection is not sorted?

## Current Stage 2 lessons

### Top K Frequent Elements

- Reference: [LeetCode 347](https://leetcode.com/problems/top-k-frequent-elements/)
- Project use: rank recurring failure signatures in QA logs.
- Simple approach: count every signature, then sort all unique signatures by
  frequency. This costs O(n + u log u), where `u` is the unique-signature count.
- Implemented approach: build a frequency map and place signatures into
  frequency buckets. Reading buckets from highest to lowest costs O(n) time and
  O(n) space.
- Production decision: equal-frequency signatures retain first-seen order so
  reports are deterministic.

Questions to practice explaining:

1. Why is a hash map useful for counting failures?
2. How does bucket indexing avoid sorting every signature?
3. What should happen when two failures have equal frequency?
4. How would the design change if the log stream never ended?

### Merge Intervals

- Reference: [LeetCode 56](https://leetcode.com/problems/merge-intervals/)
- Project use: combine nearby failure events into incident windows.
- Simple approach: repeatedly compare every interval with every other interval,
  which can degrade to O(n²).
- Implemented approach: sort by start time and make one pass, extending the
  current incident whenever the next interval overlaps. This costs O(n log n)
  time and O(n) output space.
- Production decision: interval boundaries are validated and touching windows
  count as one incident.

Questions to practice explaining:

1. Why must intervals be sorted first?
2. What invariant does the merged output maintain?
3. Should two incidents that touch at one timestamp be combined?
4. How would late or out-of-order log events affect a streaming version?

### Course Schedule

- Reference: [LeetCode 207](https://leetcode.com/problems/course-schedule/)
- Project use: detect circular dependencies between named CI jobs.
- Simple approach: repeatedly scan every dependency to find runnable jobs,
  which can do unnecessary repeated work.
- Implemented approach: Kahn's topological sort tracks each job's incoming-edge
  count and processes zero-dependency jobs with a queue. This costs O(V + E)
  time and space.
- Production decision: the wrapper validates unique job names and rejects
  dependencies that refer to unknown jobs before running the graph algorithm.

Questions to practice explaining:

1. What does each graph vertex and directed edge represent?
2. Why does a cycle prevent a complete topological ordering?
3. What does an indegree of zero mean for a CI job?
4. How would you return the actual execution order instead of a boolean?

## Twelve-problem roadmap

| Stage | Problem | Practical connection | Status |
|---|---|---|---|
| 1 | [1. Two Sum](https://leetcode.com/problems/two-sum/) | Data reconciliation | Implemented |
| 1 | [217. Contains Duplicate](https://leetcode.com/problems/contains-duplicate/) | Duplicate test-data detection | Implemented |
| 1 | [704. Binary Search](https://leetcode.com/problems/binary-search/) | Efficient sorted-record lookup | Implemented |
| 2 | [347. Top K Frequent Elements](https://leetcode.com/problems/top-k-frequent-elements/) | Failure ranking | Implemented |
| 2 | [56. Merge Intervals](https://leetcode.com/problems/merge-intervals/) | Incident consolidation | Implemented |
| 2 | [207. Course Schedule](https://leetcode.com/problems/course-schedule/) | Pipeline dependency validation | Implemented |
| 3 | [20. Valid Parentheses](https://leetcode.com/problems/valid-parentheses/) | Structured-output validation | Planned |
| 3 | [146. LRU Cache](https://leetcode.com/problems/lru-cache/) | Retrieval/result caching | Planned |
| 3 | [208. Implement Trie](https://leetcode.com/problems/implement-trie-prefix-tree/) | Document-prefix indexing | Planned |
| 4 | [72. Edit Distance](https://leetcode.com/problems/edit-distance/) | Text-difference measurement | Planned |
| 4 | [703. Kth Largest Element in a Stream](https://leetcode.com/problems/kth-largest-element-in-a-stream/) | Streaming score thresholds | Planned |
| 4 | [643. Maximum Average Subarray I](https://leetcode.com/problems/maximum-average-subarray-i/) | Rolling evaluation metrics | Planned |

The algorithm analogy does not replace production tooling. For example, edit
distance is not semantic similarity, and bracket balancing is not JSON Schema
validation. Each future lesson will document that boundary explicitly.
