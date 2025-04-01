import ctypes

def popcnt(x: int) -> int:
    """Returns the number of 1-bits in the binary representation of x (population count)."""
    return bin(x).count('1')

def Ctz(x: int) -> int:
    """Counts the number of trailing zero bits in the binary representation of x."""
    return (x & -x).bit_length() - 1 if x != 0 else 64


class Rank:
    def __init__(self):
        self.abs_hi = 0
        self.abs_lo = 0
        self.rels = [0] * 3
    
    def abs(self):
        return (self.abs_hi << 8) | self.abs_lo
    
    def set_abs(self, value):
        self.abs_hi = (value >> 8) & 0xFFFFFFFF
        self.abs_lo = value & 0xFF

class BitVector:
    def __init__(self):
        self.words = []  # 64-bit chunks
        self.ranks = []  # Rank metadata
        self.selects = []  # Select metadata
        self.n_bits = 0  # Total number of bits

    def get(self, i):
        return (self.words[i // 64] >> (i % 64)) & 1

    def set(self, i, bit):
        if bit:  # sets the bit to 1
            self.words[i // 64] |= (1 << (i % 64))
        else:  # sets the bit to 0
            self.words[i // 64] &= ~(1 << (i % 64))

    def add(self, bit):
        if self.n_bits % 256 == 0:  # extends / increase storage dynamically
            self.words.extend([0] * ((self.n_bits + 256) // 64 - len(self.words)))
        self.set(self.n_bits, bit)
        self.n_bits += 1

    def popcnt(self, x):  # return number of 1s in x 
        return bin(x).count('1')

    def ctz(self, x):  # conut trailing zeros 
        # purpose: finds position of the first 1 in x 
        return (x & -x).bit_length() - 1 if x != 0 else 64

    def build(self):
        n_blocks = len(self.words) // 4
        n_ones = 0
        self.ranks = [Rank() for _ in range(n_blocks + 1)]
        
        for block_id in range(n_blocks):
            self.ranks[block_id].set_abs(n_ones)
            for j in range(4):
                if j != 0:
                    rel = n_ones - self.ranks[block_id].abs()
                    self.ranks[block_id].rels[j - 1] = rel
                
                word_id = (block_id * 4) + j
                word = self.words[word_id]
                n_pops = self.popcnt(word)
                new_n_ones = n_ones + n_pops
                
                if ((n_ones + 255) // 256) != ((new_n_ones + 255) // 256):
                    count = n_ones
                    temp_word = word
                    while temp_word:
                        pos = self.ctz(temp_word)
                        if count % 256 == 0:
                            self.selects.append(((word_id * 64) + pos) // 256)
                            break
                        temp_word ^= 1 << pos
                        count += 1
                
                n_ones = new_n_ones
        
        self.ranks[-1].set_abs(n_ones)
        self.selects.append(len(self.words) * 64 // 256)

    def rank(self, i):
        word_id = i // 64
        bit_id = i % 64
        rank_id = word_id // 4
        rel_id = word_id % 4
        n = self.ranks[rank_id].abs()
        if rel_id:
            n += self.ranks[rank_id].rels[rel_id - 1]
        n += self.popcnt(self.words[word_id] & ((1 << bit_id) - 1))
        return n

    def select(self, i):
        block_id = i // 256
        begin = self.selects[block_id]
        end = self.selects[block_id + 1] + 1
        
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
        
        return (word_id * 64) + self.ctz(self.words[word_id] & -(1 << i))

    def size(self):
        return (8 * len(self.words)) + (len(self.ranks) * 6) + (4 * len(self.selects))

class Level:
    def __init__(self):
        self.louds = BitVector()
        self.outs = BitVector()
        self.labels = []  # List of uint8_t values
        self.offset = 0

    def size(self):
        return self.louds.size() + self.outs.size() + len(self.labels)
    
class TrieImpl:
    def __init__(self):
        self.levels = [Level() for _ in range(2)]
        self.n_keys = 0
        self.n_nodes = 1
        self.size = 0
        self.last_key = ""
        self.levels[0].louds.add(0)
        self.levels[0].louds.add(1)
        self.levels[1].louds.add(1)
        self.levels[0].outs.add(0)
        self.levels[0].labels.append(' ')

    def add(self, key: str):
        assert key > self.last_key  # keys must be inserted in lexicographical order
        if not key:
            self.levels[0].outs.set(0, 1)
            self.levels[1].offset += 1
            self.n_keys += 1
            return
        
        if len(key) + 1 >= len(self.levels):
            self.levels.extend(Level() for _ in range(len(key) + 2 - len(self.levels)))
        
        i = 0
        for i in range(len(key)):
            level = self.levels[i + 1]
            byte = key[i]
            if i == len(self.last_key) or byte != level.labels[-1]:
                level.louds.set(level.louds.n_bits - 1, 0)
                level.louds.add(1)
                level.outs.add(0)
                level.labels.append(byte)
                self.n_nodes += 1
                break
        
        for i in range(i + 1, len(key)):
            level = self.levels[i + 1]
            level.louds.add(0)
            level.louds.add(1)
            level.outs.add(0)
            level.labels.append(key[i])
            self.n_nodes += 1
        
        self.levels[len(key) + 1].louds.add(1)
        self.levels[len(key) + 1].offset += 1
        self.levels[len(key)].outs.set(self.levels[len(key)].outs.n_bits - 1, 1)
        self.n_keys += 1
        self.last_key = key

    def build(self):
        offset = 0
        for level in self.levels:
            level.louds.build()
            level.outs.build()
            offset += level.offset
            level.offset = offset
            self.size += level.size()

    def lookup(self, query: str) -> int:
        if len(query) >= len(self.levels):
            return -1
        
        node_id = 0
        for i, byte in enumerate(query):
            level = self.levels[i + 1]
            if node_id != 0:
                node_pos = level.louds.select(node_id - 1) + 1
                node_id = node_pos - node_id
            else:
                node_pos = 0

            end = node_pos
            word = level.louds.words[end // 64] >> (end % 64)
            while word == 0:
                end += 64 - (end % 64)
                word = level.louds.words[end // 64]
            end += Ctz(word)
            begin = node_id
            end = begin + end - node_pos
            
            while begin < end:
                node_id = (begin + end) // 2
                if byte < level.labels[node_id]:
                    end = node_id
                elif byte > level.labels[node_id]:
                    begin = node_id + 1
                else:
                    break
            if begin >= end:
                return -1
        
        level = self.levels[len(query)]
        return level.offset + level.outs.rank(node_id) if level.outs.get(node_id) else -1
    
    def merge(self, other_trie):
        # handle edge cases
        if not other_trie:
            return self
        if not self:
            return other_trie
        
        # Create a new trie to store the merged result
        merged_trie = TrieImpl()
        
        # Ensure enough levels exist
        max_levels = max(len(self.levels), len(other_trie.levels))
        merged_trie.levels = [Level() for _ in range(max_levels)]
        
        for i in range(max_levels):
            if i < len(self.levels) and i < len(other_trie.levels):
                self.merge_levels(merged_trie.levels[i], self.levels[i], other_trie.levels[i])
            elif i < len(self.levels):
                merged_trie.levels[i] = self.levels[i]
            else:
                merged_trie.levels[i] = other_trie.levels[i]

        # Update trie statistics
        merged_trie.n_keys = self.n_keys + other_trie.n_keys
        merged_trie.n_nodes = self.n_nodes + other_trie.n_nodes
        merged_trie.build()  # Recompute offsets & size

        return merged_trie

    def merge_levels(self, merged_level, levelA, levelB):
        """ Merges two levels into the merged_level """
        # Merge labels in lexicographical order
        labelsA = levelA.labels
        labelsB = levelB.labels
        merged_labels = sorted(set(labelsA) | set(labelsB))  # sort the level chars in order 
        
        # Merge LOUDS and Outs maintaining parent-child structure
        indexA, indexB = 0, 0
        for label in merged_labels:
            existsA = indexA < len(labelsA) and labelsA[indexA] == label
            existsB = indexB < len(labelsB) and labelsB[indexB] == label
            
            # Merge LOUDS structure
            if existsA and existsB:
                merged_level.louds.add(levelA.louds.get(indexA) | levelB.louds.get(indexB))
                merged_level.outs.add(levelA.outs.get(indexA) | levelB.outs.get(indexB))
                indexA += 1
                indexB += 1
            elif existsA:
                merged_level.louds.add(levelA.louds.get(indexA))
                merged_level.outs.add(levelA.outs.get(indexA))
                indexA += 1
            else:
                merged_level.louds.add(levelB.louds.get(indexB))
                merged_level.outs.add(levelB.outs.get(indexB))
                indexB += 1

        merged_level.labels = merged_labels

class Trie:
    def __init__(self):
        self.impl = TrieImpl()
    
    def add(self, key: str):
        self.impl.add(key)
    
    def build(self):
        self.impl.build()
    
    def lookup(self, query: str) -> int:
        return self.impl.lookup(query)
    
    def n_keys(self) -> int:
        return self.impl.n_keys
    
    def n_nodes(self) -> int:
        return self.impl.n_nodes
    
    def size(self) -> int:
        return self.impl.size
    
trie1 = TrieImpl()
trie1.add("apple")
trie1.add("banana")
print(trie1.lookup("apple"))
print(trie1.lookup("banana"))
print(trie1.lookup('add'))
# trie2 = TrieImpl()
# trie2.add("apricot")
# trie2.add("cherry")

# merged_trie = trie1.merge(trie2)

# print(merged_trie.lookup("apple"))    
# print(merged_trie.lookup("banana")) 
# print(merged_trie.lookup("apricot"))  
# print(merged_trie.lookup("cherry"))   
# print(merged_trie.lookup("grape"))
