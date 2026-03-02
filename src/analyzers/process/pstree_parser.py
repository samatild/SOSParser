#!/usr/bin/env python3
"""Parser for pstree output to create structured tree data"""

import re
from typing import Dict, List, Any, Optional


class ProcessNode:
    """Represents a single process in the tree"""
    
    def __init__(self, name: str, pid: Optional[int] = None, is_thread: bool = False):
        self.name = name
        self.pid = pid
        self.is_thread = is_thread
        self.children: List['ProcessNode'] = []
        self.parent: Optional['ProcessNode'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for template rendering"""
        return {
            'name': self.name,
            'pid': self.pid,
            'is_thread': self.is_thread,
            'children': [child.to_dict() for child in self.children]
        }


class PstreeParser:
    """Parse pstree ASCII output into structured tree"""
    
    def __init__(self):
        # Pattern to match process name and PID: "name(pid)" or "{name}(pid)" for threads
        self.process_pattern = re.compile(r'([^{]+)\((\d+)\)|{([^}]+)}\((\d+)\)')
    
    def parse(self, pstree_text: str) -> Optional[ProcessNode]:
        """
        Parse pstree text output into a tree structure.
        
        Args:
            pstree_text: Raw pstree output text
            
        Returns:
            Root ProcessNode or None if parsing fails
        """
        if not pstree_text or not pstree_text.strip():
            return None
        
        lines = pstree_text.strip().split('\n')
        if not lines:
            return None
        
        # Parse the root process (first line) - format: "name(pid)-+-..." or "name(pid)"
        root_line = lines[0].strip()
        root_node = self._parse_root_process(root_line)
        if not root_node:
            return None
        
        # Build the tree from remaining lines
        if len(lines) > 1:
            self._build_tree(root_node, lines[1:])
        
        return root_node
    
    def _parse_root_process(self, line: str) -> Optional[ProcessNode]:
        """Parse root process line: 'systemd(1)-+-...' or 'systemd(1)'"""
        # Extract process name and PID before any tree characters
        match = self.process_pattern.search(line)
        if match:
            if match.group(1):  # Regular process
                name = match.group(1).strip()
                pid = int(match.group(2))
                return ProcessNode(name=name, pid=pid, is_thread=False)
            else:  # Thread
                name = match.group(3).strip()
                pid = int(match.group(4))
                return ProcessNode(name=name, pid=pid, is_thread=True)
        return None
    
    def _parse_process_line(self, line: str) -> Optional[ProcessNode]:
        """Parse a single process line to extract name and PID"""
        # Find the process pattern in the line (after tree characters)
        match = self.process_pattern.search(line)
        if match:
            if match.group(1):  # Regular process: "name(pid)"
                name = match.group(1).strip()
                pid = int(match.group(2))
                is_thread = False
            else:  # Thread: "{name}(pid)"
                name = match.group(3).strip()
                pid = int(match.group(4))
                is_thread = True
            
            return ProcessNode(name=name, pid=pid, is_thread=is_thread)
        
        return None
    
    def _build_tree(self, root: ProcessNode, lines: List[str]):
        """Build tree structure from pstree lines"""
        if not lines:
            return
        
        # Stack to track current path in tree
        # Each entry: (node, column_position)
        stack = [(root, 0)]
        
        for line in lines:
            if not line.strip():
                continue
            
            # Find the column where the process name starts
            process_col = self._find_process_column(line)
            if process_col < 0:
                continue
            
            # Find parent node - go up the stack until we find one at a column < process_col
            while len(stack) > 1 and stack[-1][1] >= process_col:
                stack.pop()
            
            parent_node, _ = stack[-1]
            
            # Parse this line's process
            process_node = self._parse_process_line(line)
            if process_node:
                process_node.parent = parent_node
                parent_node.children.append(process_node)
                stack.append((process_node, process_col))
    
    def _find_process_column(self, line: str) -> int:
        """Find the column where the process name starts"""
        # Find where the process pattern starts
        match = self.process_pattern.search(line)
        if match:
            return match.start()
        return -1
    
    def to_html(self, root: ProcessNode, max_depth: int = 3) -> str:
        """
        Convert tree to HTML with collapsible nodes.
        
        Args:
            root: Root ProcessNode
            max_depth: Maximum depth to expand by default
            
        Returns:
            HTML string
        """
        if not root:
            return ""
        
        html_parts = []
        self._render_node_html(root, html_parts, depth=0, max_depth=max_depth, is_last=True)
        return '\n'.join(html_parts)
    
    def _render_node_html(self, node: ProcessNode, html_parts: List[str], 
                          depth: int, max_depth: int, is_last: bool):
        """Recursively render a node and its children as HTML"""
        # Determine if this node should be expanded by default
        expanded = depth < max_depth
        
        # Build the node display
        pid_str = f" <span class='process-pid'>({node.pid})</span>" if node.pid else ""
        thread_class = " process-thread" if node.is_thread else ""
        toggle_icon = "▼" if expanded else "▶"
        
        if node.children:
            # Node with children - make it collapsible
            expand_class = "expanded" if expanded else "collapsed"
            toggle_id = f"process-{node.pid or id(node)}"
            
            html_parts.append(
                f'<div class="process-node{thread_class}" data-depth="{depth}">'
                f'<span class="process-toggle" data-target="{toggle_id}">'
                f'<span class="toggle-icon">{toggle_icon}</span>'
                f'</span>'
                f'<span class="process-name">{node.name}</span>{pid_str}'
                f'</div>'
            )
            
            html_parts.append(
                f'<div class="process-children {expand_class}" id="{toggle_id}">'
            )
            
            # Render children
            for i, child in enumerate(node.children):
                is_child_last = (i == len(node.children) - 1)
                self._render_node_html(child, html_parts, depth + 1, max_depth, 
                                      is_child_last)
            
            html_parts.append('</div>')
        else:
            # Leaf node - no toggle
            html_parts.append(
                f'<div class="process-node process-leaf{thread_class}" data-depth="{depth}">'
                f'<span class="process-spacer"></span>'
                f'<span class="process-name">{node.name}</span>{pid_str}'
                f'</div>'
            )
