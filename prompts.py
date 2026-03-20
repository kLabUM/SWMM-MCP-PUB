def register_prompts(mcp):
    @mcp.prompt
    def list_models() -> str:
        """Which models are available?"""
        return "What SWMM models are available?"

    @mcp.prompt
    def describe_model(model: str) -> str:
        """Tell me about the model."""
        return f"Tell me about the SWMM model {model}."

    @mcp.prompt
    def get_pipes_and_junctions(model: str) -> str:
        """How many pipes and junctions does it have?"""
        return f"How many pipes and junctions are in the SWMM model {model}?"

    @mcp.prompt
    def largest_pipe(model: str) -> str:
        """What's the largest pipe in the network?"""
        return f"What is the largest pipe in the SWMM model {model}?"

    @mcp.prompt
    def show_network(model: str) -> str:
        """Show me my network"""
        return f"Crate a visualization of the network for the SWMM model {model}."

    @mcp.prompt
    def run_model(model: str) -> str:
        """Run a model for me"""
        return f"Run the SWMM model {model}."

    @mcp.prompt
    def compare_flow_largest_pipe(model: str) -> str:
        """Compare flow through the largest pipe for a 2-inch vs 4-inch storm."""
        return (
            f"Make a copy of the {model} SWMM model changing the rain gage section for a 2-inch storm and another copy for a 4-inch storm. Run both .inp files and plot the timeseries of the largest pipe."
        )

    @mcp.prompt
    def nodes_flood_4_inch(model: str) -> str:
        """Which nodes flood under a 4-inch storm?"""
        return (
            f"Which nodes flood under a 4-inch storm in the SWMM model {model}?"
        )

    @mcp.prompt
    def detention_recommendations(model: str) -> str:
        """Suggest detention locations to reduce downstream flooding."""
        return (
            "Where should I add detention to reduce downstream flooding in "
            f"the SWMM model {model}?"
        )

    @mcp.prompt
    def add_storage_and_rerun(model: str, node: str) -> str:
        """Add a storage unit at a node and rerun."""
        return (
            f"Create a copy of {model} model, add a 1000 cubic foot storage unit at node "
            f"{node}, rerun, and summarize the results."
        )

    @mcp.prompt
    def node_flow_timeseries(model: str, node: str) -> str:
        """Show node flow during the simulation."""
        return (
            "Show me the flow through the node "
            f"{node} during the simulation for the SWMM model {model}."
        )

    @mcp.prompt
    def compare_base_to_modified(model: str) -> str:
        """Compare base and modified scenarios."""
        return (
            "Generate a summary comparing the base SWMM model "
            f"{model} to the modified version."
        )

    @mcp.prompt
    def outfall_hydrograph_comparison(model: str, outfall: str) -> str:
        """Plot base vs. modified outfall hydrographs."""
        return (
            f"Plot the hydrograph at the outfall {outfall} for both scenarios "
            f"on one plot for the SWMM model {model}."
        )

    """
    To add in the future: (not yet supported)
    - How much does flooding decrease if I upsize pipe _ to _ ft?
    - Add a control rule that closes the orifice when depth at junction _ exceeds 1 meter.
    """
