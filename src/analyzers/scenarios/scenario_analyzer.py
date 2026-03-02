#!/usr/bin/env python3
"""Scenario-based pattern matching analyzer for sosreport"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import re
import time
from datetime import datetime
from utils.logger import Logger


@dataclass
class FileMatch:
    file_name: str
    file_path: Path
    matches: List[Dict[str, Any]]
    severity: str


@dataclass
class AdvisoryUrl:
    title: str
    url: str


@dataclass
class ScenarioResult:
    scenario_name: str
    alert_name: str
    level: str
    failure_signature: str
    workflow: str
    message: str
    recommendations: List[str]
    file_matches: List[FileMatch]
    timestamp: datetime
    advisory_urls: List[AdvisoryUrl] = None


class BaseScenarioAnalyzer:
    """Base scenario analyzer that loads JSON config and matches patterns"""
    
    def __init__(self, scenario_config_path: Path):
        self.scenario_config_path = scenario_config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load the scenario configuration from JSON file"""
        with open(self.scenario_config_path, 'r') as f:
            return json.load(f)
    
    def analyze_file(
        self, file_path: Path, file_config: Dict[str, Any]
    ) -> Optional[FileMatch]:
        """Analyze a single file based on its configuration"""
        if not file_path.exists():
            return None
        
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines(keepends=False)
                
                for pattern_config in file_config['LookFor']:
                    if pattern_config['Type'] == 'regex':
                        # Check if pattern contains multiline indicators
                        is_multiline = (
                            '\\n' in pattern_config['Pattern']
                            or '^' in pattern_config['Pattern']
                            or '$' in pattern_config['Pattern']
                        )
                        
                        if is_multiline:
                            pattern = re.compile(
                                pattern_config['Pattern'],
                                re.MULTILINE | re.DOTALL
                            )
                        else:
                            pattern = re.compile(pattern_config['Pattern'])
                        
                        # Limit matches for performance
                        max_matches = pattern_config.get('MaxMatches', 20)
                        first_half = max_matches // 2
                        last_half = max_matches - first_half
                        
                        first_matches = []
                        last_matches = []
                        total_found = 0
                        line_num = 0
                        
                        for line in lines:
                            line_num += 1
                            if pattern.search(line):
                                total_found += 1
                                
                                if len(first_matches) < first_half:
                                    first_matches.append({
                                        'pattern': pattern_config['Pattern'],
                                        'match': line.strip(),
                                        'log_line': line.strip(),
                                        'line': line_num,
                                        'severity': pattern_config['Severity']
                                    })
                                elif total_found <= max_matches:
                                    if len(last_matches) >= last_half:
                                        last_matches.pop(0)
                                    last_matches.append({
                                        'pattern': pattern_config['Pattern'],
                                        'match': line.strip(),
                                        'log_line': line.strip(),
                                        'line': line_num,
                                        'severity': pattern_config['Severity']
                                    })
                        
                        if total_found > max_matches:
                            limited_matches = first_matches + last_matches
                            hidden_count = total_found - max_matches
                            summary_msg = (
                                f"... ({hidden_count} additional matches hidden "
                                "for performance) ..."
                            )
                            limited_matches.insert(
                                first_half,
                                {
                                    'pattern': pattern_config['Pattern'],
                                    'match': summary_msg,
                                    'log_line': summary_msg,
                                    'line': 0,
                                    'severity': 'Info'
                                }
                            )
                            matches.extend(limited_matches)
                        else:
                            matches.extend(first_matches + last_matches)
        
        except Exception as e:
            Logger.error(f"Error analyzing file {file_path}: {e}")
            return None
        
        if matches:
            return FileMatch(
                file_name=file_path.name,
                file_path=file_path,
                matches=matches,
                severity=max(m['severity'] for m in matches)
            )
        return None
    
    def analyze(self, base_path: Path) -> List[ScenarioResult]:
        """Analyze the scenario based on the configuration"""
        analysis_start = time.time()
        results = []
        
        for scenario_config in self.config['ScenarioConfigs']:
            file_matches = []
            
            for file_config in scenario_config['FileConfigs']:
                # SOSReport structure is flat, not device_0 based
                if file_config['FileName'] == "*":
                    folder_path = base_path / file_config['FilePath']
                    if folder_path.is_dir():
                        for candidate_file in folder_path.iterdir():
                            if candidate_file.is_file():
                                match = self.analyze_file(
                                    candidate_file, file_config
                                )
                                if match and match.matches:
                                    file_matches.append(match)
                else:
                    file_path = (
                        base_path / file_config['FilePath'] /
                        file_config['FileName']
                    )
                    match = self.analyze_file(file_path, file_config)
                    if match and match.matches:
                        file_matches.append(match)
            
            # Only create a result if we found actual matches
            if file_matches:
                # Convert advisory URLs if present
                advisory_urls = None
                if 'AdvisoryUrls' in scenario_config:
                    advisory_urls = [
                        AdvisoryUrl(url['title'], url['url'])
                        for url in scenario_config['AdvisoryUrls']
                    ]
                
                results.append(ScenarioResult(
                    scenario_name=self.config['ScenarioName'],
                    alert_name=scenario_config['AlertName'],
                    level=scenario_config['Level'],
                    failure_signature=scenario_config['FailureSignature'],
                    workflow=scenario_config['Workflow'],
                    message=scenario_config['MessageTemplate'],
                    recommendations=scenario_config['Recommendations'],
                    file_matches=file_matches,
                    timestamp=datetime.now(),
                    advisory_urls=advisory_urls
                ))
        
        total_analysis_time = time.time() - analysis_start
        scenario_name = self.config['ScenarioName']
        Logger.debug(
            f"Scenario '{scenario_name}' completed in "
            f"{total_analysis_time:.2f}s"
        )
        return results
    
    def format_results_html(self, results: List[ScenarioResult]) -> str:
        """Format the analysis results as HTML"""
        if not results:
            return ""
        
        html = "<div class='scenario-results'>"
        for result in results:
            # Set color based on level
            level_color = {
                'Info': '#58a6ff',
                'Warning': '#d29922',
                'Error': '#f85149',
                'Critical': '#f85149',
                'High': '#ff6b6b'
            }.get(result.level, '#8b949e')
            
            # Create header with alert name and message
            html += f"""
            <div class='scenario-section'>
                <div class='scenario-header' onclick='toggleScenarioDetails(this)'>
                    <div class='scenario-header-content'>
                        <h3 style='color: {level_color}'>{result.alert_name}</h3>
                        <p class='scenario-message'>{result.message}</p>
                    </div>
                    <button class='toggle-details'>Show Details</button>
                </div>
                <div class='scenario-details'>
                    <p><strong>Level:</strong> 
                        <span style='color: {level_color}'>{result.level}</span>
                    </p>
                    <p><strong>Failure Signature:</strong> {result.failure_signature}</p>
                    <p><strong>Workflow:</strong> 
                        <a href='{result.workflow}' target='_blank'>Troubleshooting Guide</a>
                    </p>
            """
            
            # Add advisory URLs if any
            if result.advisory_urls:
                html += "<div class='advisory-links'><h4>Related Documentation:</h4><ul>"
                for advisory in result.advisory_urls:
                    html += f"<li><a href='{advisory.url}' target='_blank'>{advisory.title}</a></li>"
                html += "</ul></div>"
            
            # Add recommendations
            if result.recommendations:
                html += "<div class='recommendations'><h4>Recommendations:</h4><ul>"
                for rec in result.recommendations:
                    html += f"<li>{rec}</li>"
                html += "</ul></div>"
            
            # Add file matches
            if result.file_matches:
                html += "<div class='file-matches'>"
                for file_match in result.file_matches:
                    html += f"<div class='file-match'><h4>{file_match.file_name}</h4>"
                    html += "<div class='matches-list'>"
                    for match in file_match.matches:
                        html += f"""
                        <div class='match-item'>
                            <p><strong>Severity:</strong> 
                                <span style='color: {level_color}'>{match['severity']}</span>
                            </p>
                            <p><strong>Line:</strong> {match['line']}</p>
                            <pre>{match['log_line']}</pre>
                        </div>
                        """
                    html += "</div></div>"
                html += "</div>"
            
            html += "</div></div>"
        
        html += "</div>"
        return html
