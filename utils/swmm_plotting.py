from swmm_api import SwmmInput, SwmmOutput
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Tuple, Optional

def plot_network_map(input_file: str) -> go.Figure:
    """
    Create an interactive plot of the SWMM network showing subcatchments, nodes, and links.
    
    Args:
        input_file (str): Path to the SWMM input file
        
    Returns:
        go.Figure: Plotly figure object containing the network map
    """
    # Load input file
    inp = SwmmInput(input_file)
    
    # Create figure
    fig = go.Figure()
    
    # Extract node coordinates first as they're needed for subcatchment connections
    coordinates = {}
    if inp.COORDINATES:
        for node_id, coords in inp.COORDINATES.items():
            coordinates[node_id] = {'x': coords.x, 'y': coords.y}
    
    if not coordinates:
        raise ValueError("No coordinates found in input file")
    
    # Plot subcatchments if they exist
    if hasattr(inp, 'POLYGONS') and inp.POLYGONS is not None and hasattr(inp, 'SUBCATCHMENTS'):
        for subcatch_id, poly_data in inp.POLYGONS.items():
            # Extract polygon coordinates
            if poly_data.polygon:
                x_coords = [point[0] for point in poly_data.polygon]
                y_coords = [point[1] for point in poly_data.polygon]
                # Add first point to close the polygon
                x_coords.append(x_coords[0])
                y_coords.append(y_coords[0])
                
                # Calculate centroid for connection line
                centroid_x = sum(x_coords[:-1]) / len(x_coords[:-1])
                centroid_y = sum(y_coords[:-1]) / len(y_coords[:-1])
                
                # Plot the subcatchment
                fig.add_trace(go.Scatter(
                    x=x_coords,
                    y=y_coords,
                    fill="toself",
                    mode='lines',
                    name=f'Subcatchment {subcatch_id}',
                    line=dict(color='lightblue', width=1),
                    fillcolor='lightblue',
                    opacity=0.3,
                    text=[f'Subcatchment {subcatch_id}'],
                    hoverinfo='text',
                    legendgroup='subcatchments',
                    showlegend=True
                ))
                
                # Add connection to outlet if outlet information exists
                if hasattr(inp, 'SUBCATCHMENTS') and inp.SUBCATCHMENTS is not None and subcatch_id in inp.SUBCATCHMENTS:
                    subcatch_data = inp.SUBCATCHMENTS[subcatch_id]
                    if hasattr(subcatch_data, 'outlet'):
                        outlet_id = subcatch_data.outlet
                        if outlet_id in coordinates:
                            fig.add_trace(go.Scatter(
                                x=[centroid_x, coordinates[outlet_id]['x']],
                                y=[centroid_y, coordinates[outlet_id]['y']],
                                mode='lines',
                                name=f'Subcatchment {subcatch_id} → {outlet_id}',
                                line=dict(
                                    color='green',
                                    width=1,
                                    dash='dot'
                                ),
                                text=[f'Subcatchment {subcatch_id} → {outlet_id}'],
                                hoverinfo='text',
                                legendgroup='subcatchment_connections',
                                showlegend=False
                            ))
    

    # Plot links (conduits, orifices, etc.)
    link_types = {
        'CONDUITS': {'color': 'gray', 'width': 2, 'dash': 'solid'},
        'ORIFICES': {'color': 'purple', 'width': 2, 'dash': 'dash'},
        'WEIRS': {'color': 'orange', 'width': 2, 'dash': 'dot'},
        'OUTLETS': {'color': 'brown', 'width': 2, 'dash': 'dashdot'},
        'PUMPS': {'color': 'red', 'width': 2, 'dash': 'longdash'}
    }
    
    # Plot each type of link
    for link_type, style in link_types.items():
        if hasattr(inp, link_type):
            links = getattr(inp, link_type)
            if links is not None:
                for link_id, link_data in links.items():
                    fig.add_trace(go.Scatter(
                        x=[coordinates[link_data.from_node]['x'], coordinates[link_data.to_node]['x']],
                        y=[coordinates[link_data.from_node]['y'], coordinates[link_data.to_node]['y']],
                        mode='lines',
                        name=f"{link_type[:-1].title()} {link_id}",
                        line=dict(
                            color=style['color'],
                            width=style['width'],
                            dash=style['dash']
                        ),
                        text=[f"{link_type[:-1].title()} {link_id}<br>{link_data.from_node} → {link_data.to_node}"],
                        hoverinfo='text',
                        legendgroup=link_type[:-1].lower(),
                        showlegend=True
                    ))
    
    # Determine node types from SWMM sections
    node_types = {
        'STORAGE': {'prefix': 'SU', 'color': 'blue', 'size': 15},
        'OUTFALL': {'prefix': 'OF', 'color': 'green', 'size': 15},
        'DIVIDER': {'prefix': 'D', 'color': 'yellow', 'size': 12},
        'JUNCTION': {'prefix': 'J', 'color': 'black', 'size': 8}
    }
    
    # Build node type mapping
    node_type_map = {}
    for section in ['STORAGE', 'OUTFALLS', 'DIVIDERS', 'JUNCTIONS']:
        if hasattr(inp, section) and getattr(inp, section) is not None:
            section_data = getattr(inp, section)
            # Remove 'S' from end of section name if it exists
            section_type = section[:-1] if section.endswith('S') else section
            for node_id in section_data:
                node_type_map[node_id] = section_type
    
    for node_id, coord in coordinates.items():
        # Determine node type
        node_style = None
        node_type = node_type_map.get(node_id, 'JUNCTION')  # Default to junction if not found
        for type_name, type_info in node_types.items():
            if node_type.startswith(type_name):
                node_style = type_info
                break
        if not node_style:  # Fallback to junction if no match
            node_style = node_types['JUNCTION']
        
        fig.add_trace(go.Scatter(
            x=[coord['x']],
            y=[coord['y']],
            mode='markers+text',
            name=node_id,
            text=[node_id],
            marker=dict(
                size=node_style['size'],
                color=node_style['color']
            ),
            textposition="top center",
            showlegend=False
        ))
    
    # Update layout
    fig.update_layout(
        title='SWMM Network Map',  # Changed to "Map" instead of "Layout"
        showlegend=True,
        hovermode='closest',
        paper_bgcolor="rgb(245, 244, 237)",
        plot_bgcolor="rgb(245, 244, 237)",
        xaxis=dict(
            title='',  # Removed axis title since it's a map
            showgrid=False,  # Remove gridlines
            zeroline=False,   # Remove zero line
            fixedrange=False  # Enable panning in x direction
        ),
        yaxis=dict(
            title='',  # Removed axis title since it's a map
            scaleanchor='x',
            scaleratio=1,
            showgrid=False,  # Remove gridlines
            zeroline=False,   # Remove zero line
            fixedrange=False  # Enable panning in y direction
        ),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.02,
            itemsizing='constant'
        ),
        dragmode='pan',  # Make pan the default drag mode instead of zoom
        modebar=dict(
            bgcolor='rgba(0,0,0,0)',  # Transparent background
            color='#555',  # Dark gray icons
            remove=['autoScale2d']  # Remove less commonly used buttons
        ),
        annotations=[
            dict(
                x=1.1,
                y=0.5,
                xref='paper',
                yref='paper',
                text='Areas:<br>' +
                     '█ Subcatchments (light blue)<br><br>' +
                     'Node Types:<br>' +
                     '● Storage Units (blue)<br>' +
                     '● Outfalls (green)<br>' +
                     '● Dividers (yellow)<br>' +
                     '● Junctions (black)<br><br>' +
                     'Link Types:<br>' +
                     '― Conduits (gray)<br>' +
                     '-- Orifices (purple)<br>' +
                     '·· Weirs (orange)<br>' +
                     '-· Outlets (brown)<br>' +
                     '— Pumps (red)',
                showarrow=False,
                align='left'
            )
        ],
        margin=dict(r=100)
    )
    
    return fig

def plot_link_timeseries(output_file: str, 
                        link_ids: List[str], 
                        variables: Optional[List[str]] = None) -> go.Figure:
    """
    Create an interactive plot of link time series data.
    
    Args:
        output_file (str): Path to the SWMM output file
        link_ids (List[str]): List of link IDs to plot
        variables (Optional[List[str]]): List of variables to plot. If None, plots flow
        
    Returns:
        go.Figure: Plotly figure object containing the time series plots
        
    Raises:
        ValueError: If output file doesn't exist or if specified links are not found
    """
    try:
        # Load output file
        output = SwmmOutput(output_file)
    except FileNotFoundError:
        raise ValueError(f"Output file not found: {output_file}")
    except Exception as e:
        raise ValueError(f"Error reading output file: {str(e)}")
    
    if variables is None:
        variables = ['flow']
        
    # Verify links exist in output
    available_links = output.labels.get('link', [])
    missing_links = [link for link in link_ids if link not in available_links]
    if missing_links:
        raise ValueError(f"Links not found in output: {', '.join(missing_links)}")
    
    # Create subplot figure
    fig = make_subplots(
        rows=len(link_ids), 
        cols=1,
        subplot_titles=[f'Link {link}' for link in link_ids]
    )
    
    # Plot each link
    for i, link_id in enumerate(link_ids, start=1):
        link_data = output.get_part('link', link_id)
        df = pd.DataFrame(link_data)
        
        for var in variables:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[var],
                    name=f'{link_id} {var}',
                    line=dict(width=2)
                ),
                row=i, col=1
            )
    
    # Update layout
    fig.update_layout(
        height=300 * len(link_ids),
        title_text="Link Time Series Analysis",
        showlegend=True,
        hovermode='x unified'
    )
    
    # Update axes labels
    fig.update_xaxes(title_text="Time", row=len(link_ids), col=1)
    for i in range(1, len(link_ids) + 1):
        fig.update_yaxes(title_text="Value", row=i, col=1)
    
    return fig

def plot_node_timeseries(output_file: str, 
                        node_ids: List[str],
                        variables: Optional[List[str]] = None) -> go.Figure:
    """
    Create an interactive plot of node time series data.
    
    Args:
        output_file (str): Path to the SWMM output file
        node_ids (List[str]): List of node IDs to plot
        variables (Optional[List[str]]): List of variables to plot. If None, plots depth
        
    Returns:
        go.Figure: Plotly figure object containing the time series plots
        
    Raises:
        ValueError: If output file doesn't exist or if specified nodes are not found
    """
    try:
        # Load output file
        output = SwmmOutput(output_file)
    except FileNotFoundError:
        raise ValueError(f"Output file not found: {output_file}")
    except Exception as e:
        raise ValueError(f"Error reading output file: {str(e)}")
    
    if variables is None:
        variables = ['depth']
        
    # Verify nodes exist in output
    available_nodes = output.labels.get('node', [])
    missing_nodes = [node for node in node_ids if node not in available_nodes]
    if missing_nodes:
        raise ValueError(f"Nodes not found in output: {', '.join(missing_nodes)}")
    
    # Create subplot figure
    fig = make_subplots(
        rows=len(node_ids), 
        cols=1,
        subplot_titles=[f'Node {node}' for node in node_ids]
    )
    
    # Plot each node
    for i, node_id in enumerate(node_ids, start=1):
        node_data = output.get_part('node', node_id)
        df = pd.DataFrame(node_data)
        
        for var in variables:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[var],
                    name=f'{node_id} {var}',
                    line=dict(width=2)
                ),
                row=i, col=1
            )
    
    # Update layout
    fig.update_layout(
        height=300 * len(node_ids),
        title_text="Node Time Series Analysis",
        showlegend=True,
        hovermode='x unified'
    )
    
    # Update axes labels
    fig.update_xaxes(title_text="Time", row=len(node_ids), col=1)
    for i in range(1, len(node_ids) + 1):
        fig.update_yaxes(title_text="Value", row=i, col=1)
    
    return fig



def plot_timeseries_generalized(fig: go.Figure, series: pd.Series, x_label = None, y_label = None, trace_name = None) -> go.Figure:
    """
    Create an interactive plot from a generic pandas Series.

    Args:
        series (pd.Series): Pandas Series with datetime index and numeric values

    Returns:
        go.Figure: Plotly figure object containing the time series plot
    """
    #fig = go.Figure()

    name = "Series"
    if series.name:
        name = " ".join(str(series.name).split(';')[-2:])

    if not trace_name:
        trace_name = name

    fig.add_trace(go.Scatter(
        x=series.index,
        y=series.values,
        name=trace_name,
        line=dict(width=2),
        mode='lines'
    ))

    if x_label is None:
        x_label = "Time"
    if y_label is None:
        y_label = name

    # Update layout
    fig.update_layout(
        title=name,
        xaxis_title=x_label,
        yaxis_title=y_label,
        hovermode='x unified',
        showlegend=True,
        paper_bgcolor="rgb(245, 244, 237)",
        plot_bgcolor="rgb(245, 244, 237)",
    )

    return fig

# Example usage:
if __name__ == "__main__":
    # Example network map
    network_fig = plot_network_map("models/DemoModel.inp")
    network_fig.write_html("network_map.html")
    
    # Example time series for large pipes
    timeseries_fig = plot_link_timeseries(
        "models/DemoModel.out",
        link_ids=['C8', 'C9', 'C10'],
        variables=['flow', 'capacity']
    )
    timeseries_fig.write_html("link_timeseries.html")
