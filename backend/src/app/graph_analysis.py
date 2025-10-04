# import networkx as nx
# from sqlalchemy.orm import Session
# from sqlalchemy import or_
# from app.models import Transaction, User
# import plotly.graph_objects as go
# import json

# def build_and_analyze_graph(db: Session, root_user_id: int, hops: int = 2) -> dict:
#     """
#     Builds and analyzes a "local neighborhood" graph to prevent out-of-memory errors.
#     """
#     print(f"Starting LOCAL graph analysis for user {root_user_id} with {hops} hops...")
    
#     # --- Step 1: Find the local neighborhood of users ---
#     nodes_to_include = {root_user_id}
#     current_layer = {root_user_id}

#     for _ in range(hops):
#         if not current_layer: break
        
#         # Find all users connected to the current layer of nodes
#         query = db.query(Transaction.from_user_id, Transaction.to_user_id).filter(
#             or_(
#                 Transaction.from_user_id.in_(current_layer),
#                 Transaction.to_user_id.in_(current_layer)
#             )
#         ).distinct()

#         next_layer = set()
#         for from_id, to_id in query:
#             if from_id: next_layer.add(from_id)
#             if to_id: next_layer.add(to_id)
        
#         new_nodes = next_layer - nodes_to_include
#         if not new_nodes: break
        
#         nodes_to_include.update(new_nodes)
#         current_layer = new_nodes

#     print(f"Found {len(nodes_to_include)} users in the local neighborhood.")

#     # --- Step 2: Fetch only the transactions between these users ---
#     local_txs = db.query(Transaction).filter(
#         Transaction.from_user_id.in_(nodes_to_include),
#         Transaction.to_user_id.in_(nodes_to_include)
#     ).all()

#     if not local_txs:
#         return {"error": "No P2P transactions found in the local neighborhood."}

#     # --- Step 3: Build the smaller, local graph ---
#     G = nx.DiGraph()
#     for tx in local_txs:
#         G.add_edge(tx.from_user_id, tx.to_user_id, weight=tx.amount)

#     if not G.has_node(root_user_id):
#         return {"error": "User not in P2P graph after filtering."}
        
#     print(f"Local graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        
#     # --- Step 4: Analysis (on the smaller graph) ---
#     user_cycles = [c for c in nx.simple_cycles(G) if root_user_id in c]
#     pagerank = nx.pagerank(G, weight='weight')
#     betweenness = nx.betweenness_centrality(G, weight='weight')
    
#     analysis_findings = {
#         "cycles": user_cycles,
#         "pagerank_score": pagerank.get(root_user_id, 0),
#         "betweenness_score": betweenness.get(root_user_id, 0),
#     }

#     # --- Step 5: Visualization (on the smaller graph) ---
#     pos = nx.spring_layout(G, k=0.8, iterations=100, seed=42)
    
#     edge_annotations = []
#     for edge in G.edges():
#         x0, y0 = pos[edge[0]]
#         x1, y1 = pos[edge[1]]
#         edge_annotations.append(go.layout.Annotation(x=x1, y=y1, ax=x0, ay=y0, xref='x', yref='y', axref='x', ayref='y', showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1, arrowcolor='#666'))

#     node_x, node_y, node_text, node_colors, node_sizes = [], [], [], [], []
#     all_user_map = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(nodes_to_include)).all()}
    
#     node_strengths = dict(G.degree(weight='weight'))
#     min_strength = min(node_strengths.values()) if node_strengths else 1
#     max_strength = max(node_strengths.values()) if node_strengths else 1

#     for node in G.nodes():
#         x, y = pos[node]
#         node_x.append(x)
#         node_y.append(y)
#         node_text.append(f"<b>{all_user_map.get(node, f'ID: {node}')}</b><br>Influence (PageRank): {pagerank.get(node, 0):.3f}")

#         strength = node_strengths.get(node, 0)
#         size = 10 + 30 * ((strength - min_strength) / (max_strength - min_strength + 1e-6))
#         node_sizes.append(size)

#         if node == root_user_id: node_colors.append('#f48fb1')
#         elif any(node in cycle for cycle in user_cycles): node_colors.append('#ff6f00')
#         elif G.in_degree(node) == 0: node_colors.append('#90caf9')
#         else: node_colors.append('#81c784')

#     node_trace = go.Scatter(x=node_x, y=node_y, mode='markers', hoverinfo='text', text=node_text, marker=dict(color=node_colors, size=node_sizes, line_width=2, line_color='#FFF'))
    
#     # We create an edge trace separately for a cleaner graph (no lines go through markers)
#     edge_x_coords, edge_y_coords = [], []
#     for edge in G.edges():
#         x0, y0 = pos[edge[0]]
#         x1, y1 = pos[edge[1]]
#         edge_x_coords.extend([x0, x1, None])
#         edge_y_coords.extend([y0, y1, None])
    
#     edge_trace = go.Scatter(x=edge_x_coords, y=edge_y_coords, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

#     fig = go.Figure(data=[edge_trace, node_trace],
#         layout=go.Layout(
#             showlegend=False, hovermode='closest', margin=dict(b=0,l=0,r=0,t=0),
#             annotations=edge_annotations,
#             xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
#             yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
#         )
#     )
    
#     return {
#         "findings": analysis_findings,
#         "plot_data": json.loads(fig.to_json())
#     }






















import networkx as nx
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import Transaction, User
import plotly.graph_objects as go
import json

def build_and_analyze_graph(db: Session, root_user_id: int) -> dict:
    """
    Builds an EGO GRAPH - only showing the user and their direct connections.
    This is extremely fast and memory-efficient.
    """
    print(f"Starting EGO graph analysis for user {root_user_id}...")
    
    # --- Step 1: Fetch ONLY direct transactions for the root user ---
    direct_txs = db.query(Transaction).filter(
        or_(
            Transaction.from_user_id == root_user_id,
            Transaction.to_user_id == root_user_id
        )
    ).all()

    if not direct_txs:
        return {"error": "User has no P2P transactions to graph."}

    # --- Step 2: Build the small, local graph ---
    G = nx.DiGraph()
    for tx in direct_txs:
        if tx.from_user_id and tx.to_user_id:
            G.add_edge(tx.from_user_id, tx.to_user_id, weight=tx.amount)

    if not G.nodes:
        return {"error": "Could not build graph from user's transactions."}
        
    print(f"Ego graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        
    # --- Step 3: Analysis (on the small graph) ---
    # We can't find long cycles, but we can still get basic stats.
    pagerank = nx.pagerank(G) if G.nodes else {}
    
    analysis_findings = {
        "cycles": [], # Ego graph is unlikely to have cycles unless it's a direct back-and-forth
        "pagerank_score": pagerank.get(root_user_id, 0),
        "betweenness_score": 0, # Not meaningful on an ego graph
    }

    # --- Step 4: Visualization (This part is fine) ---
    pos = nx.spring_layout(G)
    
    edge_annotations = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_annotations.append(go.layout.Annotation(x=x1, y=y1, ax=x0, ay=y0, xref='x', yref='y', axref='x', ayref='y', showarrow=True, arrowhead=2, arrowsize=2, arrowwidth=1.5, arrowcolor='#888'))

    node_x, node_y, node_text, node_colors, node_sizes = [], [], [], [], []
    all_user_ids = list(G.nodes())
    user_map = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(all_user_ids)).all()}
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"<b>{user_map.get(node, f'ID: {node}')}</b>")

        if node == root_user_id:
            node_colors.append('#f48fb1') # Pink
            node_sizes.append(30)
        else:
            node_colors.append('#90caf9') # Blue
            node_sizes.append(20)

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="top center", marker=dict(color=node_colors, size=node_sizes, line_width=2))
    
    edge_x_coords, edge_y_coords = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x_coords.extend([x0, x1, None])
        edge_y_coords.extend([y0, y1, None])
    
    edge_trace = go.Scatter(x=edge_x_coords, y=edge_y_coords, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines')

    fig = go.Figure(data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
            annotations=edge_annotations,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )
    
    return {
        "findings": analysis_findings,
        "plot_data": json.loads(fig.to_json())
    }