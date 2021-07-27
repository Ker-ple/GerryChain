def district_adjacency(partition, pop_updater):
    """Forms the district adjacency graph of a `Partition`."""
    pairs = set(
        (partition.assignment[src], partition.assignment[dst])
        for src, dst in partition['cut_edges']
    )
    G = nx.Graph()
    G.add_edges_from(pairs)
    for dist, pop in partition[pop_updater].items():
        G.nodes[dist]['population'] = pop
        G.nodes[dist]['children'] = [dist]
    return G

def partition_from_contracted_graph(partition, contracted):
    """Maps a contracted district graph back to a `Partition` of multi-member districts."""
    dist_mapping = {}
    for idx, node in enumerate(contracted.nodes):
        for child in contracted.nodes[node]['children']:
            dist_mapping[child] = idx
    contracted_assignment = {k: dist_mapping[v] for k, v in partition.assignment.items()}
    return GeographicPartition(partition.graph, assignment=contracted_assignment, updaters=partition.updaters)

def contract_nodes(dist_graph, D, n_tries=1000, verbose=False):
    dist_graph = deepcopy(dist_graph)
    D = D.copy()
    done = set()
    n_parts = len(dist_graph)
    assert sum(D) == n_parts  # Constraint: conservation of districts.
    for i in range(n_tries): # We expect this algorithm to fail often.
        if verbose:
            print(
                'iter:', i,
                '\tparts to merge:', D,
                '\tdistricts merged:', done,
                '\tdistrict nodes:', {n: dist_graph.nodes[n]['children'] for n in dist_graph.nodes}
            )
        if not D: # Step 6: repeat 2-5 until D is empty
            break
        n_to_merge = choice(D)
    
    # Choose a district (which may or may not have multiple children) to start
    # merging other districts into. Constraints:
    #  * len(district.children) ≤ n_to_merge,
    #  * district not merged yet
    # But the second condition implies the first condition,
    # as all nodes are initially single-member.
    district = choice(list(dist_graph.nodes))
    while district in done:
        district = choice(list(dist_graph.nodes))
      
    # Start greedily contracting neighbors into the chosen district.
    contracted = deepcopy(dist_graph)
    while len(contracted.nodes[district]['children']) < n_to_merge:
      # Constraint: `district` has at least one neighbor such that 
      #     len(dist_graph.nodes[district]['children']) +
      #     len(dist_graph.nodes[neighbor]['children']) ≤ n_to_merge
        district_pieces = len(contracted.nodes[district]['children'])
        neighbor_pieces = {
            n: len(contracted.nodes[n]['children'])
            for n in contracted.neighbors(district)
        }
        if not neighbor_pieces or min(neighbor_pieces.values()) + district_pieces > n_to_merge:
            break # give up!

        random_neighbor = choice(list(contracted.neighbors(district)))
        if district_pieces + neighbor_pieces[random_neighbor] <= n_to_merge:
        # We've found a valid merge.
            contracted.nodes[district]['population'] += contracted.nodes[random_neighbor]['population']
            contracted.nodes[district]['children'] += contracted.nodes[random_neighbor]['children']
            contracted.remove_node(random_neighbor)

    # Check if we've successfully merged and update state.
    if len(contracted.nodes[district]['children']) == n_to_merge:  # step 5
        D.remove(n_to_merge)
        dist_graph = contracted
        done |= set(dist_graph.nodes[district]['children'])
      
    if len(done) == n_parts:
        return dist_graph
    if verbose:
        print('Warning: merging failed. Try again...', done, len(dist_graph))
    return None

def multi_member_seed(partition, pop_updater, D, n_tries=100):
  dist_graph = district_adjacency(partition, pop_updater)
  for _ in range(n_tries):
    contracted = contract_nodes(dist_graph, D)
    if contracted:
      seed = partition_from_contracted_graph(partition, contracted)       
      dist_seats = {k: round(v / pop_target) for k, v in seed['population'].items()}      
      return (seed, dist_seats)
  print("Couldn't find a valid merge after", n_tries, "tries.")