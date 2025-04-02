# **Merging Two LOUDS-Tries**

## **Task**  
I would like to add another method to the `Trie` class declared in `louds-trie.hpp`:  

```cpp
Trie *merge_trie(const Trie& trie1, const Trie& trie2);
```

The `merge_trie` routine should merge the two tries passed as inputs and create a merged LOUDS-trie as the output. The function signature can be modified if needed for convenience. The merging should efficiently exploit the trie structure of the input tries, and the output trie should be in the space-efficient **LOUDS format**.

---

## **Approach (Thought Process)**  

Since the original source code is written in **C++**, a language I am not familiar with, the first step I took was to **translate `louds-trie.cpp` into Python**. This helped me better understand the code logic and structure.

Instead of writing the `merge_trie` method within the `Trie` class, I chose to implement it as an **individual function** for simplicity and easier debugging.

### **Logic for `merge_trie`**  

1. **Extract all keys from each trie.**  
2. **Remove duplicate keys and sort them** in alphabetical order (since the original trie-building algorithm requires keys to be added in alphabetical order). Then, use the provided `add()` and `build()` methods to construct the merged trie.  
3. The **key extraction method** uses a simple **depth-first search (DFS)** algorithm to traverse both tries and return the stored words.

This approach ensures that the merging process remains **efficient** while maintaining the **space-efficient LOUDS format**.


## **Deliverables**  

I added two new files to the original repository:  

- **`merge.py`** – Contains the individual `merge_trie(trie1, trie2)` logic.  
- **`update_louds_trie.py`** – Includes all the classes translated from C++ to Python, the `merge_trie(trie1, trie2)` method, as well as a simple test case to demonstrate that the code works as expected.  