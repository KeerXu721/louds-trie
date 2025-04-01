def merge(trie1, trie2):
    merged_trie = Trie()
    
    def merge_levels(level1, level2, merged_level):
        idx1, idx2 = 0, 0
        while idx1 < len(level1.labels) or idx2 < len(level2.labels):
            if idx1 < len(level1.labels) and (idx2 >= len(level2.labels) or level1.labels[idx1] < level2.labels[idx2]):
                merged_level.add_node(level1.labels[idx1], level1.outs[idx1])
                idx1 += 1
            elif idx2 < len(level2.labels) and (idx1 >= len(level1.labels) or level1.labels[idx1] > level2.labels[idx2]):
                merged_level.add_node(level2.labels[idx2], level2.outs[idx2])
                idx2 += 1
            else:  # Same character, merge them
                merged_level.add_node(level1.labels[idx1], level1.outs[idx1] or level2.outs[idx2])
                idx1 += 1
                idx2 += 1
        merged_level.finalize()

    max_levels = max(len(trie1.levels), len(trie2.levels))
    
    for i in range(max_levels):
        level1 = trie1.levels[i] if i < len(trie1.levels) else LOUDS()
        level2 = trie2.levels[i] if i < len(trie2.levels) else LOUDS()
        merged_level = LOUDS()
        merge_levels(level1, level2, merged_level)
        merged_trie.levels.append(merged_level)
    
    return merged_trie