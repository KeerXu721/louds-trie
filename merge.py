def merge_trie(trie1, trie2):
    """
    Merge two LOUDS-tries efficiently.
    
    Args:
        trie1: First input trie
        trie2: Second input trie
        
    Returns:
        A new merged LOUDS-trie
    """
    # Extract all keys from both tries
    keys1 = extract_keys(trie1)
    keys2 = extract_keys(trie2)
    
    # Merge and sort keys, remove duplicates and keep alphabetical order
    merged_keys = sorted(set(keys1) | set(keys2))
    
    # Create a new trie with the merged keys
    merged_trie = Trie()
    for key in merged_keys:
        merged_trie.add(key)
    
    # Build the trie indexes
    merged_trie.build()
    
    return merged_trie


def extract_keys(trie):
    """
    Extract all keys from a trie.
    
    Args:
        trie: Input trie
        
    Returns:
        List of keys in the trie
    """
    keys = []
    
    def dfs(node_id, level, current_key):
        """Depth-first traversal to extract keys."""
        # Check if this node is a terminal
        if level < len(trie.levels) and trie.levels[level].outs.get(node_id):
            keys.append(current_key)  # add the key to results if reaches the end 
        
        # Skip if reached the maximum level
        if level + 1 >= len(trie.levels):
            return
        
        # Find children
        next_level = trie.levels[level + 1]
        node_pos = 0
        
        if node_id != 0:
            node_pos = next_level.louds.select(node_id - 1) + 1
            start_child = node_pos - node_id
        else:
            start_child = 0
        
        # Determine the range of children
        end_pos = node_pos
        while end_pos < next_level.louds.n_bits and next_level.louds.get(end_pos) == 0:
            end_pos += 1
        
        end_child = start_child + end_pos - node_pos
        
        # Visit each child
        for child_id in range(start_child, end_child):
            char = chr(next_level.labels[child_id])
            dfs(child_id, level + 1, current_key + char)
    
    # Start DFS from the root
    dfs(0, 0, "")
    return keys