from collections import defaultdict

class BitVector:

    class Rank:
        def __init__(self):
            self.abs_hi = 0
            self.abs_lo = 0
            self.rels = [0, 0, 0]
        
        def abs(self):
            return (self.abs_hi << 8) | self.abs_lo
        
        def set_abs(self, abs_val):
            self.abs_hi = abs_val >> 8
            self.abs_lo = abs_val & 0xFF
    
    def __init__(self):
        self.words = []  # 64-bit chunks of the bit vector
        self.ranks = []  # Rank metadata for each block
        self.selects = []  # Select metadata
        self.n_bits = 0  # Total number of bits in the vector
    
    def get(self, i):
        """Returns the bit at index i."""
        return (self.words[i // 64] >> (i % 64)) & 1
    
    def set(self, i, bit):
        """Sets the bit at index i to the input bit value."""
        if bit:
            self.words[i // 64] |= (1 << (i % 64))
        else:
            self.words[i // 64] &= ~(1 << (i % 64))
    
    def add(self, bit):
        """Adds a bit to the vector."""
        if self.n_bits % 256 == 0:
            self.words.extend([0] * ((256 + self.n_bits - len(self.words) * 64) // 64))
        self.set(self.n_bits, bit)
        self.n_bits += 1
    
    def build(self):
        n_blocks = len(self.words) // 4
        n_ones = 0
        self.ranks = [self.Rank() for _ in range(n_blocks + 1)]
        self.selects = []
        
        for block_id in range(n_blocks):
            self.ranks[block_id].set_abs(n_ones)
            for j in range(4):
                if j != 0:
                    rel = n_ones - self.ranks[block_id].abs()
                    self.ranks[block_id].rels[j - 1] = rel
                
                word_id = (block_id * 4) + j
                word = self.words[word_id]
                n_pops = bin(word).count('1')  # Count set bits
                new_n_ones = n_ones + n_pops
                
                if ((n_ones + 255) // 256) != ((new_n_ones + 255) // 256):
                    count = n_ones
                    temp_word = word
                    while temp_word != 0:
                        pos = (temp_word & -temp_word).bit_length() - 1  
                        if count % 256 == 0:
                            self.selects.append(((word_id * 64) + pos) // 256)
                            break
                        temp_word ^= 1 << pos
                        count += 1
                
                n_ones = new_n_ones
        
        self.ranks[-1].set_abs(n_ones)
        self.selects.append(len(self.words) * 64 // 256)
    
    def rank(self, i):
        """Returns the number of 1-bits in the range [0, i)."""
        word_id = i // 64
        bit_id = i % 64
        rank_id = word_id // 4
        rel_id = word_id % 4
        
        n = self.ranks[rank_id].abs()
        if rel_id != 0:
            n += self.ranks[rank_id].rels[rel_id - 1]
        
        # Count 1-bits in the current word up to bit_id
        mask = (1 << bit_id) - 1
        n += bin(self.words[word_id] & mask).count('1')
        
        return n
    
    def select(self, i):
        """Returns the position of the (i+1)-th 1-bit."""
        block_id = i // 256
        begin = self.selects[block_id]
        end = self.selects[block_id + 1] + 1
        
        if begin + 10 >= end:
            while i >= self.ranks[begin + 1].abs():
                begin += 1
        else:
            while begin + 1 < end:
                middle = (begin + end) // 2
                if i < self.ranks[middle].abs():
                    end = middle
                else:
                    begin = middle
        
        rank_id = begin
        i -= self.ranks[rank_id].abs()
        
        word_id = rank_id * 4
        if i < self.ranks[rank_id].rels[1]:
            if i >= self.ranks[rank_id].rels[0]:
                word_id += 1
                i -= self.ranks[rank_id].rels[0]
        elif i < self.ranks[rank_id].rels[2]:
            word_id += 2
            i -= self.ranks[rank_id].rels[1]
        else:
            word_id += 3
            i -= self.ranks[rank_id].rels[2]
        
        word = self.words[word_id]
        count = 0
        pos = 0
        
        while count <= i:
            if (word >> pos) & 1:
                if count == i:
                    break
                count += 1
            pos += 1
        
        return (word_id * 64) + pos
    
    def size(self):
        """Returns the size in bytes."""
        return (8 * len(self.words) +  # words (uint64_t)
                16 * len(self.ranks) +  # Ranks (struct Rank)
                4 * len(self.selects))  # selects (uint32_t)


class Level:
    """Represents a level in the LOUDS trie."""
    
    def __init__(self):
        self.louds = BitVector()  # LOUDS bitvector
        self.outs = BitVector()   # Output bitvector marking terminals
        self.labels = []          # Edge labels stored in ord number 
        self.offset = 0           # Offset for this level
    
    def size(self):
        """Returns the size in bytes."""
        return self.louds.size() + self.outs.size() + len(self.labels)


class Trie:
    
    def __init__(self):
        self.levels = [Level(), Level()]  # Initialize with two levels
        self.n_keys = 0
        self.n_nodes = 1
        self.size_bytes = 0
        self.last_key = ""
        
        # Initialize root node
        self.levels[0].louds.add(0)
        self.levels[0].louds.add(1)
        self.levels[1].louds.add(1)
        self.levels[0].outs.add(0)
        self.levels[0].labels.append(' ')  # Root label
    
    def add(self, key):
        """Add a word to the trie."""
        assert key > self.last_key  # Keys must be inserted in lexicographical order
        
        if not key:
            self.levels[0].outs.set(0, 1)  # Mark root as terminal
            self.levels[1].offset += 1
            self.n_keys += 1
            return
        
        if len(key) + 1 >= len(self.levels):
            # Expand levels if needed
            self.levels.extend([Level() for _ in range(len(key) + 2 - len(self.levels))])
        
        i = 0
        # Find the first position where the key differs from the last key
        for i in range(len(key)):
            level = self.levels[i + 1]
            byte = ord(key[i])
            
            if (i == len(self.last_key)) or (byte != level.labels[-1] if level.labels else True):
                if level.louds.n_bits > 0:
                    level.louds.set(level.louds.n_bits - 1, 0)
                level.louds.add(1)
                level.outs.add(0)
                level.labels.append(byte)
                self.n_nodes += 1
                break
        
        # Add remaining characters
        for i in range(i + 1, len(key)):
            level = self.levels[i + 1]
            level.louds.add(0)
            level.louds.add(1)
            level.outs.add(0)
            level.labels.append(ord(key[i]))
            self.n_nodes += 1
        
        # Mark the end of the key
        self.levels[len(key) + 1].louds.add(1)
        self.levels[len(key) + 1].offset += 1
        self.levels[len(key)].outs.set(self.levels[len(key)].outs.n_bits - 1, 1)
        self.n_keys += 1
        self.last_key = key
    
    def build(self):
        offset = 0
        for i in range(len(self.levels)):
            level = self.levels[i]
            level.louds.build()
            level.outs.build()
            offset += level.offset
            level.offset = offset
            self.size_bytes += level.size()
    
    def lookup(self, query):
        """Look up a query in the trie. -1 indicating the query does not exists in the trie"""
        if len(query) >= len(self.levels):
            return -1
        
        node_id = 0  #ith node in this level
        for i in range(len(query)):
            level = self.levels[i + 1]
            node_pos = 0
            
            if node_id != 0:
                node_pos = level.louds.select(node_id - 1) + 1
                node_id = node_pos - node_id
            
            # Find the end of the current node's children
            end = node_pos
            while end < level.louds.n_bits and level.louds.get(end) == 0:
                end += 1
            
            begin = node_id
            end = begin + end - node_pos
            
            byte = ord(query[i])
            found = False
            
            # Binary search for the character
            while begin < end:
                node_id = (begin + end) // 2
                if byte < level.labels[node_id]:
                    end = node_id
                elif byte > level.labels[node_id]:
                    begin = node_id + 1
                else:
                    found = True
                    break
            
            if not found:
                return -1
        
        level = self.levels[len(query)]
        if not level.outs.get(node_id):
            return -1
            
        return level.offset + level.outs.rank(node_id) 

    def find_parent_char(self, child_label_idx, louds, parent_labels):
        """
        Given an index into the child level's labels list,
        find the character of the parent node from the parent level's label list.
        """
        # Step 1: Find the position of the child_label_idx-th 0 in the LOUDS bitvector
        pos = 0
        zero_count = 0

        while zero_count <= child_label_idx:
            if louds.get(pos) == 0:
                zero_count += 1
            pos += 1
        pos -= 1  # Go back to the position of the 0 bit

        # Step 2: Count the number of 1s before this 0
        parent_id = louds.rank(pos)

        # Step 3: Return the corresponding parent label
        return parent_labels[parent_id] if parent_id < len(parent_labels) else None


    def merge_trie(self, other_trie):
        # TODO finish the code here 

        """
        Merge another LOUDS trie into this trie by directly manipulating the BitVectors.
        Basic Logic:
        for each level on both tries:
            extract labels from both tries
            create a parent-label mapping (to make sure the trie structure is kept correctly)

            first sort the parent nodes in alphabetical order
            update the corresponding nodes' louds and outs BitVector in alphabetical order 
                
        """
        if not other_trie or other_trie.n_keys == 0:
            return  # Nothing to merge
        
        # Keep track of merged keys count
        merged_key_count = 0
        
        # Process the root level separately (level 0)
        # Merge terminal status of root nodes
        if not self.levels[0].outs.get(0) and other_trie.levels[0].outs.get(0):
            self.levels[0].outs.set(0, 1)
            merged_key_count += 1
        
        level_maps = defaultdict(dict)

        for i in range(1, max(len(self.levels), len(other_trie.levels))):
            self_level = self.levels[i]
            other_level = other_trie.levels[i]
            self_labels = self_level.labels
            other_labels = other_level.labels

            parent_label = defaultdict(set)
            for s_l in range(len(self_labels)):
                idx_1 = self.find_parent_char(s_l, self_level.louds, self.levels[i-1].labels)
                parent_label[idx_1].add(self_labels[s_l])

            for o_l in range(len(other_labels)):
                idx_1 = self.find_parent_char(o_l, other_level.louds, other_trie.levels[i-1].labels)
                parent_label[idx_1].add(other_labels[o_l])

            level_maps[i] = parent_label

        for level in level_maps.keys():
            parent_label = level_maps[level]
            new_labels = []
            if len(parent_label) == 1 and list(parent_label.keys())[0] == ' ':
                # Parent is the root, add the current level characters alphabetically
                labels = sorted(parent_label[' '])
                for label_idx in range(len(labels)):
                    new_labels.append(labels[label_idx])
                    self.levels[i].louds.set(label_idx, 0)  # Set 1 for each child
                self.levels[i].louds.set(len(labels), 1)  # End of the level
                self.levels[i].labels = new_labels

            else:
                # Sort by the parent node, and sort the corresponding children's nodes
                parent_sorted = dict(sorted(parent_label.items()))
                cur_idx = 0  # Track index across all children
                for k, v in parent_sorted.items():
                    sorted_labels = sorted(v)
                    cur_idx = 0
                    for label_idx in range(len(sorted_labels)):
                        new_labels.append(sorted_labels[label_idx])
                        self.levels[i].louds.set(cur_idx, 0)  
                        cur_idx += 1
                    self.levels[i].louds.set(cur_idx, 1)  # End of children for parent

                self.levels[i].labels = new_labels 


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

# tests with sample code
if __name__ == "__main__":
    # Create and populate the first trie
    trie1 = Trie()
    for word in ["add", "apl", "app", "bce"]:
        trie1.add(word)
    trie1.build()
    trie1.lookup("apple")
    # Create and populate the second trie
    trie2 = Trie()
    for word in ["adf" ,"ama", "amb", "cde"]:
        trie2.add(word)
    trie2.build()
    
    # Merge the tries
    trie1.merge_trie(trie2)
    trie1.build()

    # merge_tries_in_place(trie1, trie2)
    
    # Verify the merged trie
    test_words = ["a"]
    for word in test_words:
        result = trie1.lookup(word)
        print(f"Word '{word}': {'Found' if result >= 0 else 'Not found'}")
