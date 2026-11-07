

def get_correct_position(tool):
    """Get position of a tool that is usable for FlowView positions"""
    try:
        result = tool.SaveSettings()
        for tool in result["Tools"].values():
            if "ViewInfo" in tool and "Pos" in tool["ViewInfo"]:
                pos = tool["ViewInfo"]["Pos"]
                return pos[1], pos[2]
    except (KeyError, AttributeError, TypeError):
        pass
    return None

    
def set_flow_position(flow, position, scale=None):
    """Set FlowView offset position and scaling factor"""
    
    if scale is None:
        # Preserve scaling
        scale = flow.GetScale()
    
    # Use a temporary bookmark to set flow position
    NAME = "__TMP__"
    flow.InsertBookmark(NAME)
    bookmarks = flow.GetBookmarkList()
    # Get index by name
    index = next(key for key, value in bookmarks.items() if value["Name"] == NAME)
    
    bookmark = bookmarks[index]
    bookmark["Offset"][1] = position[0]
    bookmark["Offset"][2] = position[1]
    bookmark["Scale"] = scale
    flow.SetBookmarkList(bookmarks)
    
    flow.GoToBookmark(NAME)
    
    # flow.DeleteBookmark doesn't work so we set the 
    # BookmarkList ourselves minus the temp bookmark
    bookmarks.pop(index)
    flow.SetBookmarkList(bookmarks)
    
    
def frame_tools(flow, tools):
    """Frame tools in the FlowView"""
    
    # TODO: Take into account size of a Sticky Note or Backdrop
    # TODO: Take into the visual size of a Tool (e.g. with thumbnail)
    
    positions = [get_correct_position(tool) for tool in tools]
    positions = [p for p in positions if p is not None]  # Filter out None values

    if len(positions) == 0:
        # No valid positions found, do nothing
        return
    
    if len(positions) > 1:
      
        # Get bounding box of the tools
        bb_min_x = min(p[0] for p in positions)
        bb_min_y = min(p[1] for p in positions)
        bb_max_x = max(p[0] for p in positions)
        bb_max_y = max(p[1] for p in positions)

        center = [(bb_min_x + bb_max_x) / 2.0, (bb_min_y + bb_max_y) / 2.0]
        size = [(bb_max_x - bb_min_x), (bb_max_y - bb_min_y)]

        # Get flow size
        flow_attrs = flow.GetAttrs()
        flow_size = [flow_attrs["VIEWN_Right"] - flow_attrs["VIEWN_Left"], flow_attrs["VIEWN_Bottom"] - flow_attrs["VIEWN_Top"]]

        # Get relative scale of tool distance compared to the flow screen space
        relative_size = [a / b for a, b in zip(flow_size, size)]

        # Take the smallest scale factor of the two axes
        scale = min(relative_size) / 2.0
        
    else:
        center = positions[0]
        scale = None

        
    set_flow_position(flow, position=center, scale=scale)
    
    
def frame_selected(flow):
    """Frame selected tools in the flow view"""
    comp = flow.Composition()
    tools = list(comp.GetToolList(True).values())
    
    # If no tools are selected, zoom out to maximum using center of all nodes
    if len(tools) == 0:
        # Get all tools to calculate their center
        all_tools = list(comp.GetToolList(False).values())
        if len(all_tools) > 0:
            # Use frame_tools logic but with all tools, then override scale
            positions = [get_correct_position(tool) for tool in all_tools]
            positions = [p for p in positions if p is not None]  # Filter out None values
            
            if len(positions) > 0:
                if len(positions) > 1:
                    bb_min_x = min(p[0] for p in positions)
                    bb_min_y = min(p[1] for p in positions)
                    bb_max_x = max(p[0] for p in positions)
                    bb_max_y = max(p[1] for p in positions)
                    center = [(bb_min_x + bb_max_x) / 2.0, (bb_min_y + bb_max_y) / 2.0]
                else:
                    center = positions[0]
            else:
                center = [0, 0]
        else:
            center = [0, 0]
        # Set a very small scale for maximum zoom out
        scale = 0.01  # Very small scale = maximum zoom out
        set_flow_position(flow, position=center, scale=scale)
    else:
        frame_tools(flow, tools)


def frame_all(flow):
    """Frame all tools in the flow view"""
    comp = flow.Composition()
    tools = comp.GetToolList(False).values()
    frame_tools(flow, tools)


# Example usage
comp = fu.GetCurrentComp()
flow = comp.CurrentFrame.FlowView
frame_selected(flow)
