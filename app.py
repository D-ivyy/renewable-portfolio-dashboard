import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, ctx, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import gaussian_kde
import warnings
import base64
import io
from typing import Optional, List, Dict, Any
warnings.filterwarnings('ignore')

# Initialize Dash app with modern theme
app = dash.Dash(__name__, 
                external_stylesheets=[
                    dbc.themes.BOOTSTRAP,
                    "https://use.fontawesome.com/releases/v6.1.1/css/all.css",
                    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
                ],
                suppress_callback_exceptions=True)
app.title = "Renewable Portfolio Dashboard - Parquet"

# Modern color palette matching plots.ipynb exactly
COLORS = {
    'generation': '#70AD47',  # Green
    'price_da': '#ED7D31',    # Orange for day-ahead
    'price_rt': '#4472C4',    # Blue for real-time
    'revenue_da': '#ED7D31',  # Orange
    'revenue_rt': '#FFC000',  # Yellow
    'historical': '#8B0000',  # Dark red for historical average
    'background': '#f8f9fa',
    'card': '#ffffff',
    'text': '#2c3e50',
    'text_muted': '#6c757d',
    'border': '#dee2e6'
}

MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']

class RenewablePortfolioDashboard:
    """Dashboard for Renewable Portfolio LLC - Optimized for performance with Parquet files
    
    Note: This dashboard looks for parquet files in 'Renewable Portfolio LLC_parquet' folder
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            # Look for both possible folder names - with underscore!
            if Path("Renewable Portfolio LLC_parquet").exists():
                self.portfolio_path = Path("Renewable Portfolio LLC_parquet")
            elif Path("Renewable Portfolio LLC").exists():
                self.portfolio_path = Path("Renewable Portfolio LLC")
            else:
                self.portfolio_path = Path.cwd()
        else:
            self.portfolio_path = Path(base_path)
            
        if self.portfolio_path.name in ['Renewable Portfolio LLC', 'Renewable Portfolio LLC_parquet']:
            print(f"✅ Working in portfolio directory: {self.portfolio_path}")
        else:
            # Check for parquet folder first (with underscore)
            if (self.portfolio_path / 'Renewable Portfolio LLC_parquet').exists():
                self.portfolio_path = self.portfolio_path / 'Renewable Portfolio LLC_parquet'
                print(f"✅ Found portfolio at: {self.portfolio_path}")
            elif (self.portfolio_path / 'Renewable Portfolio LLC').exists():
                self.portfolio_path = self.portfolio_path / 'Renewable Portfolio LLC'
                print(f"✅ Found portfolio at: {self.portfolio_path}")
        
        # Cache for performance
        self._sites_cache = None
        self._files_cache = {}
        
        # Print final path being used
        print(f"📂 Dashboard initialized with path: {self.portfolio_path.absolute()}")
        
        # Quick check for parquet files
        parquet_count = len(list(self.portfolio_path.rglob("*.parquet")))
        print(f"📊 Found {parquet_count} parquet files in the directory")
    
    def get_all_sites(self) -> List[str]:
        """Get all site folders with caching"""
        if self._sites_cache is None:
            sites = []
            for item in self.portfolio_path.iterdir():
                if item.is_dir() and not item.name.startswith('bootstrap_selections'):
                    if ((item / 'Generation').exists() or (item / 'Price_da').exists() or
                        (item / 'Price_rt').exists() or (item / 'Revenue_da').exists() or
                        (item / 'Revenue_rt').exists()):
                        sites.append(item.name)
            self._sites_cache = sorted(sites)
            print(f"📋 Found {len(self._sites_cache)} sites: {', '.join(self._sites_cache[:3])}{'...' if len(self._sites_cache) > 3 else ''}")
        return self._sites_cache
    
    def clean_site_name(self, site_name: str) -> str:
        """Clean up site name for display"""
        clean_name = site_name.replace('_LLC', '').replace('_Power', '')
        clean_name = clean_name.replace('_', ' ').title()
        return clean_name
    
    def get_available_files(self, site_name: str) -> List[Dict[str, Any]]:
        """Get all available files for a site with caching - now looks for parquet files"""
        cache_key = f"{site_name}_files"
        if cache_key not in self._files_cache:
            site_path = self.portfolio_path / site_name
            files_info = []
            
            # Define the structure to check
            folders = {
                'Generation': ['forecast/distribution', 'forecast/timeseries', 'historical'],
                'Price_da': ['forecast/distribution', 'forecast/timeseries', 'historical'],
                'Price_rt': ['forecast/distribution', 'forecast/timeseries', 'historical'],
                'Revenue_da': ['forecast/distribution', 'forecast/timeseries', 'historical'],
                'Revenue_rt': ['forecast/distribution', 'forecast/timeseries', 'historical']
            }
            
            for main_folder, subfolders in folders.items():
                main_path = site_path / main_folder
                if main_path.exists():
                    for subfolder in subfolders:
                        sub_path = main_path / subfolder
                        if sub_path.exists():
                            # Look for parquet files instead of csv
                            for file in sub_path.glob('*.parquet'):
                                files_info.append({
                                    'metric': main_folder,
                                    'type': subfolder.split('/')[-1],
                                    'file': file.name,
                                    'path': str(file),
                                    'size': f"{file.stat().st_size / 1024:.1f} KB"
                                })
            
            self._files_cache[cache_key] = files_info
        return self._files_cache[cache_key]
    
    def find_distribution_file(self, site_name: str, metric_type: str, temporal: str) -> Optional[Path]:
        """Find distribution file - now looks for parquet files"""
        folder_map = {
            'generation': 'Generation',
            'price_da': 'Price_da',
            'price_rt': 'Price_rt',
            'revenue_da': 'Revenue_da',
            'revenue_rt': 'Revenue_rt'
        }
        
        metric_folder = self.portfolio_path / site_name / folder_map.get(metric_type, metric_type)
        if not metric_folder.exists():
            print(f"⚠️  Metric folder not found: {metric_folder}")
            return None
        
        dist_path = metric_folder / 'forecast' / 'distribution'
        if not dist_path.exists():
            print(f"⚠️  Distribution path not found: {dist_path}")
            return None
        
        # Look for parquet file instead of csv
        filename = f"{site_name}_{metric_type}_{temporal}_distribution.parquet"
        file_path = dist_path / filename
        
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            # List what files ARE in the directory
            print(f"   Available files in {dist_path}:")
            for f in dist_path.glob("*.parquet"):
                print(f"   - {f.name}")
        
        return file_path if file_path.exists() else None
    
    def find_timeseries_file(self, site_name: str, metric_type: str, temporal: str) -> Optional[Path]:
        """Find timeseries file - now looks for parquet files"""
        folder_map = {
            'generation': 'Generation',
            'price_da': 'Price_da',
            'price_rt': 'Price_rt',
            'revenue_da': 'Revenue_da',
            'revenue_rt': 'Revenue_rt'
        }
        
        metric_folder = self.portfolio_path / site_name / folder_map.get(metric_type, metric_type)
        if not metric_folder.exists():
            return None
        
        ts_path = metric_folder / 'forecast' / 'timeseries'
        if not ts_path.exists():
            return None
        
        # Look for parquet file instead of csv
        filename = f"{site_name}_{metric_type}_{temporal}_timeseries.parquet"
        file_path = ts_path / filename
        
        return file_path if file_path.exists() else None
    
    def find_historical_file(self, site_name: str, metric_type: str = 'generation', temporal: str = 'hourly') -> Optional[Path]:
        """Find historical file for any metric type and temporal resolution - now looks for parquet files"""
        folder_map = {
            'generation': 'Generation',
            'price_da': 'Price_da',
            'price_rt': 'Price_rt',
            'revenue_da': 'Revenue_da',
            'revenue_rt': 'Revenue_rt'
        }
        
        metric_folder = self.portfolio_path / site_name / folder_map.get(metric_type, metric_type)
        hist_path = metric_folder / 'historical'
        
        if not hist_path.exists():
            return None
        
        # Construct filename based on metric type and temporal resolution - parquet extension
        filename = f'{site_name}_{metric_type}_{temporal}_historical.parquet'
        file_path = hist_path / filename
        
        return file_path if file_path.exists() else None
    
    def calculate_historical_average(self, site_name: str, metric_type: str, temporal: str, num_years: int = 10) -> Optional[pd.DataFrame]:
        """Calculate historical average for the last N years - now reads parquet files"""
        hist_file = self.find_historical_file(site_name, metric_type, temporal)
        if not hist_file:
            return None
        
        try:
            # Read parquet file instead of csv
            df = pd.read_parquet(hist_file)
            
            # Get the column name for the metric
            if metric_type == 'generation':
                if temporal == 'hourly':
                    value_col = 'generation_mw'
                else:
                    value_col = f'{temporal}_generation_mwh'
            elif metric_type in ['price_da', 'price_rt']:
                value_col = 'weighted_price' if temporal in ['daily', 'monthly'] else metric_type
            elif metric_type in ['revenue_da', 'revenue_rt']:
                value_col = metric_type
            
            # Check if column exists
            if value_col not in df.columns:
                print(f"Warning: Column {value_col} not found in historical data")
                return None
            
            # Get last N complete years
            years = sorted(df['year'].unique())
            if len(years) < num_years:
                last_years = years
            else:
                last_years = years[-num_years:]
            
            # Filter for last N years
            df_recent = df[df['year'].isin(last_years)].copy()
            
            if temporal == 'monthly':
                # For monthly, group by month
                avg_df = df_recent.groupby('month')[value_col].mean().reset_index()
                avg_df.columns = ['month', 'historical_avg']
                return avg_df
            
            elif temporal == 'daily':
                # For daily, group by month and day
                avg_df = df_recent.groupby(['month', 'day'])[value_col].mean().reset_index()
                avg_df.columns = ['month', 'day', 'historical_avg']
                return avg_df
            
            elif temporal == 'hourly':
                if metric_type == 'generation' or 'price' in metric_type:
                    # For diurnal pattern, group by hour
                    avg_df = df_recent.groupby('hour')[value_col].mean().reset_index()
                    avg_df.columns = ['hour', 'historical_avg']
                else:
                    # For hourly timeseries, group by month, day, hour
                    avg_df = df_recent.groupby(['month', 'day', 'hour'])[value_col].mean().reset_index()
                    avg_df.columns = ['month', 'day', 'hour', 'historical_avg']
                return avg_df
            
        except Exception as e:
            print(f"Error calculating historical average: {str(e)}")
            return None

# Initialize dashboard
dashboard = RenewablePortfolioDashboard()
print("="*60)
print("🔍 Dashboard initialization complete")
print("="*60)

# Define header styles
header_style = {
    'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'color': 'white',
    'padding': '2rem 0',
    'marginBottom': '2rem',
    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
}

# Define card styles
nav_card_style = {
    'cursor': 'pointer',
    'borderRadius': '12px',
    'transition': 'all 0.3s ease',
    'border': '2px solid transparent',
    'marginBottom': '1rem'
}

nav_card_active_style = {
    **nav_card_style,
    'borderColor': '#667eea',
    'backgroundColor': '#f8f9ff'
}

# Create layout with improved structure and design
app.layout = html.Div([
    
    # Header with gradient background
    html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H3([
                        html.I(className="fas fa-solar-panel me-2"),
                        "Renewable Portfolio Analytics"
                    ], className="text-center mb-0", 
                       style={'font-weight': '600', 'letter-spacing': '-0.3px'})
                ])
            ])
        ])
    ], style={**header_style, 'padding': '1rem 0'}),
    
    dbc.Container([
        dbc.Row([
            # Left sidebar for navigation
            dbc.Col([
                # Site Selection Card
                dbc.Card([
                    dbc.CardBody([
                        html.Label("Select Renewable Site", 
                                  className="fw-bold mb-2", 
                                  style={'color': COLORS['text']}),
                        dcc.Dropdown(
                            id='site-dropdown',
                            options=[{'label': dashboard.clean_site_name(site), 'value': site} 
                                    for site in dashboard.get_all_sites()],
                            value=dashboard.get_all_sites()[0] if dashboard.get_all_sites() else None,
                            style={'font-size': '14px'},
                            className="shadow-sm",
                            placeholder="Select a site..."
                        ),
                        html.Div(id="quick-stats", className="text-muted mt-2 small")
                    ])
                ], className="shadow-sm mb-3", style={'border': 'none', 'border-radius': '12px'}),
                
                # Main Navigation
                html.H6("Analysis Type", className="text-muted mb-3"),
                dbc.Button([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-sun fa-lg mb-1", 
                                  style={'color': COLORS['generation']}),
                            html.H6("Generation", className="mb-0 fw-bold")
                        ], className="text-center py-2")
                    ], style=nav_card_style)
                ], id="nav-generation", color="link", className="p-0 border-0 w-100 mb-2"),
                
                dbc.Button([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-dollar-sign fa-lg mb-1", 
                                  style={'color': COLORS['price_da']}),
                            html.H6("Price", className="mb-0 fw-bold")
                        ], className="text-center py-2")
                    ], style=nav_card_style)
                ], id="nav-price", color="link", className="p-0 border-0 w-100 mb-2"),
                
                dbc.Button([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-chart-line fa-lg mb-1", 
                                  style={'color': COLORS['revenue_da']}),
                            html.H6("Revenue", className="mb-0 fw-bold")
                        ], className="text-center py-2")
                    ], style=nav_card_style)
                ], id="nav-revenue", color="link", className="p-0 border-0 w-100 mb-2"),
                
                dbc.Button([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-check-circle fa-lg mb-1", 
                                  style={'color': '#28a745'}),
                            html.H6("Validation", className="mb-0 fw-bold")
                        ], className="text-center py-2")
                    ], style=nav_card_style)
                ], id="nav-validation", color="link", className="p-0 border-0 w-100 mb-2"),
                
                dbc.Button([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-table fa-lg mb-1", 
                                  style={'color': '#6f42c1'}),
                            html.H6("Data View", className="mb-0 fw-bold")
                        ], className="text-center py-2")
                    ], style=nav_card_style)
                ], id="nav-data", color="link", className="p-0 border-0 w-100 mb-2"),
                
                dbc.Button([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-briefcase fa-lg mb-1", 
                                  style={'color': '#e83e8c'}),
                            html.H6("Portfolio View", className="mb-0 fw-bold")
                        ], className="text-center py-2")
                    ], style=nav_card_style)
                ], id="nav-portfolio", color="link", className="p-0 border-0 w-100 mb-2"),
                
                # Sub-navigation area
                html.Div(id='sub-navigation', className="mt-4")
                
            ], md=3, className="pe-4"),
            
            # Right side for main content
            dbc.Col([
                # Sub-navigation area (moved to top horizontally)
                html.Div(id='sub-navigation-top', className="mb-3"),
                
                # Plot type selection area (moved to top horizontally)
                html.Div(id='plot-type-buttons', className="mb-3"),
                
                dcc.Loading(
                    id="loading",
                    type="default",
                    fullscreen=False,
                    overlay_style={"backgroundColor": "rgba(255,255,255,0.9)"},
                    children=html.Div(id="main-content")
                )
            ], md=9)
        ])
    ], fluid=True),
    
    # Store components for state management
    dcc.Store(id='current-tab', data='generation'),
    dcc.Store(id='current-plot-type', data='monthly-forecast'),
    dcc.Store(id='price-type', data='da'),
    dcc.Store(id='revenue-type', data='da'),
    dcc.Store(id='view-mode', data='forecast'),  # 'forecast' or 'historical'
    
    # Suggestion Box (floating)
    html.Div([
        dbc.Tooltip(
            "Share your suggestions and feedback",
            target="suggestion-btn",
            placement="left"
        ),
        dbc.Button([
            html.I(className="fas fa-lightbulb", style={'fontSize': '1.2rem'})
        ], id="suggestion-btn", color="primary", size="lg", 
           className="rounded-circle shadow-lg",
           style={
               'position': 'fixed',
               'top': '20px',
               'right': '20px',
               'zIndex': '9999',
               'width': '60px',
               'height': '60px',
               'padding': '0'
           }),
        
        dbc.Modal([
            dbc.ModalHeader([
                html.H4([
                    html.I(className="fas fa-lightbulb me-2"),
                    "Share Your Suggestion"
                ])
            ]),
            dbc.ModalBody([
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Your Name (Optional)", className="fw-bold"),
                            dbc.Input(id="suggestion-name", type="text", placeholder="Enter your name...")
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Email (Optional)", className="fw-bold"),
                            dbc.Input(id="suggestion-email", type="email", placeholder="Enter your email...")
                        ], md=6)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Current View", className="fw-bold"),
                            dbc.Input(id="suggestion-context", type="text", disabled=True)
                        ])
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Your Suggestion", className="fw-bold"),
                            dbc.Textarea(id="suggestion-text", 
                                       placeholder="Share your ideas, feedback, or suggestions for improving this dashboard...",
                                       rows=4, style={'resize': 'vertical'})
                        ])
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Priority", className="fw-bold"),
                            dbc.Select(id="suggestion-priority",
                                     options=[
                                         {"label": "Low", "value": "low"},
                                         {"label": "Medium", "value": "medium"},
                                         {"label": "High", "value": "high"}
                                     ],
                                     value="medium")
                        ], md=6)
                    ])
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="suggestion-cancel", color="secondary", className="me-2"),
                dbc.Button("Submit Suggestion", id="suggestion-submit", color="primary")
            ])
        ], id="suggestion-modal", size="lg", is_open=False),
        
        # Toast for confirmation
        dbc.Toast(
            "Thank you! Your suggestion has been submitted.",
            id="suggestion-toast",
            header="Suggestion Submitted",
            is_open=False,
            dismissable=True,
            duration=4000,
            icon="success",
            style={"position": "fixed", "top": 90, "right": 20, "width": 350, "zIndex": 9999}
        )
    ]),
    
], style={'backgroundColor': '#f0f2f5', 'min-height': '100vh'})

# Callback for quick stats
@app.callback(
    Output('quick-stats', 'children'),
    Input('site-dropdown', 'value')
)
def update_quick_stats(site_name):
    if not site_name:
        return "No site selected"
    
    total_sites = len(dashboard.get_all_sites())
    
    return f"{total_sites} sites available"

# Callback for navigation card clicks
@app.callback(
    [Output('current-tab', 'data'),
     Output('nav-generation', 'children'),
     Output('nav-price', 'children'),
     Output('nav-revenue', 'children'),
     Output('nav-validation', 'children'),
     Output('nav-data', 'children'),
     Output('nav-portfolio', 'children')],
    [Input('nav-generation', 'n_clicks'),
     Input('nav-price', 'n_clicks'),
     Input('nav-revenue', 'n_clicks'),
     Input('nav-validation', 'n_clicks'),
     Input('nav-data', 'n_clicks'),
     Input('nav-portfolio', 'n_clicks')],
    State('current-tab', 'data'),
    prevent_initial_call=False
)
def handle_nav_clicks(gen_clicks, price_clicks, rev_clicks, val_clicks, data_clicks, portfolio_clicks, current_tab):
    try:
        # Determine which card was clicked
        triggered = ctx.triggered_id
        
        if triggered == 'nav-generation':
            new_tab = 'generation'
        elif triggered == 'nav-price':
            new_tab = 'price'
        elif triggered == 'nav-revenue':
            new_tab = 'revenue'
        elif triggered == 'nav-validation':
            new_tab = 'validation'
        elif triggered == 'nav-data':
            new_tab = 'data'
        elif triggered == 'nav-portfolio':
            new_tab = 'portfolio'
        else:
            new_tab = current_tab or 'generation'
        
        # Ensure we always have a valid tab
        if new_tab not in ['generation', 'price', 'revenue', 'validation', 'data', 'portfolio']:
            new_tab = 'generation'
        
        # Create card content with appropriate styles
        def create_card_content(icon_class, icon_color, title, is_active):
            style = nav_card_active_style if is_active else nav_card_style
            return dbc.Card([
                dbc.CardBody([
                    html.I(className=f"{icon_class} fa-lg mb-1", style={'color': icon_color}),
                    html.H6(title, className="mb-0 fw-bold")
                ], className="text-center py-2")
            ], style=style)
        
        gen_card = create_card_content("fas fa-sun", COLORS['generation'], "Generation", 
                                       new_tab == 'generation')
        price_card = create_card_content("fas fa-dollar-sign", COLORS['price_da'], "Price",
                                        new_tab == 'price')
        rev_card = create_card_content("fas fa-chart-line", COLORS['revenue_da'], "Revenue",
                                       new_tab == 'revenue')
        val_card = create_card_content("fas fa-check-circle", '#28a745', "Validation",
                                       new_tab == 'validation')
        data_card = create_card_content("fas fa-table", '#6f42c1', "Data View",
                                       new_tab == 'data')
        portfolio_card = create_card_content("fas fa-briefcase", '#e83e8c', "Portfolio View",
                                           new_tab == 'portfolio')
        
        return new_tab, gen_card, price_card, rev_card, val_card, data_card, portfolio_card
    except Exception:
        # Fallback to generation tab if anything goes wrong
        new_tab = 'generation'
        def create_card_content(icon_class, icon_color, title, is_active):
            style = nav_card_active_style if is_active else nav_card_style
            return dbc.Card([
                dbc.CardBody([
                    html.I(className=f"{icon_class} fa-lg mb-1", style={'color': icon_color}),
                    html.H6(title, className="mb-0 fw-bold")
                ], className="text-center py-2")
            ], style=style)
        
        gen_card = create_card_content("fas fa-sun", COLORS['generation'], "Generation", True)
        price_card = create_card_content("fas fa-dollar-sign", COLORS['price_da'], "Price", False)
        rev_card = create_card_content("fas fa-chart-line", COLORS['revenue_da'], "Revenue", False)
        val_card = create_card_content("fas fa-check-circle", '#28a745', "Validation", False)
        data_card = create_card_content("fas fa-table", '#6f42c1', "Data View", False)
        portfolio_card = create_card_content("fas fa-briefcase", '#e83e8c', "Portfolio View", False)
        
        return new_tab, gen_card, price_card, rev_card, val_card, data_card, portfolio_card

# Callback for sub-navigation (horizontal at top)
@app.callback(
    Output('sub-navigation-top', 'children'),
    [Input('current-tab', 'data')]
)
def update_sub_navigation_top(current_tab):
    if current_tab == 'price':
        return dbc.Card([
            dbc.CardBody([
                html.H6("Price Type", className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Day-Ahead", id="price-da-btn", 
                                  color="warning", outline=False, 
                                  size="sm", className="w-100")
                    ], width="auto", className="me-2"),
                    dbc.Col([
                        dbc.Button("Real-Time", id="price-rt-btn", 
                                  color="primary", outline=True, 
                                  size="sm", className="w-100")
                    ], width="auto")
                ])
            ], className="py-2")
        ], className="shadow-sm", style={'border': 'none', 'border-radius': '12px'})
    elif current_tab == 'revenue':
        return dbc.Card([
            dbc.CardBody([
                html.H6("Revenue Type", className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Day-Ahead", id="revenue-da-btn", 
                                  color="warning", outline=False, 
                                  size="sm", className="w-100")
                    ], width="auto", className="me-2"),
                    dbc.Col([
                        dbc.Button("Real-Time", id="revenue-rt-btn", 
                                  color="warning", outline=True, 
                                  size="sm", className="w-100")
                    ], width="auto")
                ])
            ], className="py-2")
        ], className="shadow-sm", style={'border': 'none', 'border-radius': '12px'})
    else:
        return None

# Keep the old sub-navigation for backward compatibility (now empty)
@app.callback(
    Output('sub-navigation', 'children'),
    [Input('current-tab', 'data')]
)
def update_sub_navigation(current_tab):
    return None

# Callback for price sub-navigation
@app.callback(
    [Output('price-da-btn', 'outline'),
     Output('price-rt-btn', 'outline'),
     Output('price-type', 'data')],
    [Input('price-da-btn', 'n_clicks'),
     Input('price-rt-btn', 'n_clicks')],
    [State('price-type', 'data'),
     State('current-tab', 'data')],
    prevent_initial_call=True
)
def handle_price_nav(da_clicks, rt_clicks, current_type, current_tab):
    if current_tab != 'price':
        raise dash.exceptions.PreventUpdate
    
    triggered = ctx.triggered_id
    
    if triggered == 'price-da-btn':
        return False, True, 'da'
    elif triggered == 'price-rt-btn':
        return True, False, 'rt'
    else:
        return current_type == 'rt', current_type == 'da', current_type

# Callback for revenue sub-navigation
@app.callback(
    [Output('revenue-da-btn', 'outline'),
     Output('revenue-rt-btn', 'outline'),
     Output('revenue-type', 'data')],
    [Input('revenue-da-btn', 'n_clicks'),
     Input('revenue-rt-btn', 'n_clicks')],
    [State('revenue-type', 'data'),
     State('current-tab', 'data')],
    prevent_initial_call=True
)
def handle_revenue_nav(da_clicks, rt_clicks, current_type, current_tab):
    if current_tab != 'revenue':
        raise dash.exceptions.PreventUpdate
    
    triggered = ctx.triggered_id
    
    if triggered == 'revenue-da-btn':
        return False, True, 'da'
    elif triggered == 'revenue-rt-btn':
        return True, False, 'rt'
    else:
        return current_type == 'rt', current_type == 'da', current_type

# Callback for plot type buttons
@app.callback(
    [Output('plot-type-buttons', 'children'),
     Output('current-plot-type', 'data')],
    [Input('current-tab', 'data'),
     Input('price-type', 'data'),
     Input('revenue-type', 'data')],
    State('current-plot-type', 'data')
)
def update_plot_buttons(current_tab, price_type, revenue_type, current_plot_type):
    if current_tab == 'generation':
        buttons = [
            {'label': 'Daily Forecast', 'value': 'daily-forecast', 'icon': 'fa-calendar-day'},
            {'label': 'Monthly Forecast', 'value': 'monthly-forecast', 'icon': 'fa-chart-bar'},
            {'label': 'Diurnal Pattern', 'value': 'diurnal-pattern', 'icon': 'fa-clock'},
            {'label': 'Annual Distribution', 'value': 'annual-distribution', 'icon': 'fa-chart-area'},
            {'label': 'GHI vs Generation (Hour)', 'value': 'ghi-hour', 'icon': 'fa-sun'},
            {'label': 'GHI vs Generation (Temp)', 'value': 'ghi-temp', 'icon': 'fa-temperature-high'}
        ]
    elif current_tab == 'price':
        buttons = [
            {'label': 'Daily Forecast', 'value': 'daily-forecast', 'icon': 'fa-calendar-day'},
            {'label': 'Monthly Forecast', 'value': 'monthly-forecast', 'icon': 'fa-chart-bar'},
            {'label': 'Diurnal Pattern', 'value': 'diurnal-pattern', 'icon': 'fa-clock'},
            {'label': 'Duration Curve', 'value': 'duration-curve', 'icon': 'fa-sort-amount-down'}
        ]
    elif current_tab == 'revenue':
        buttons = [
            {'label': 'Daily Forecast', 'value': 'daily-forecast', 'icon': 'fa-calendar-day'},
            {'label': 'Monthly Forecast', 'value': 'monthly-forecast', 'icon': 'fa-chart-bar'},
            {'label': 'Annual Distribution', 'value': 'annual-distribution', 'icon': 'fa-chart-area'}
        ]
    elif current_tab == 'data':
        buttons = [
            {'label': 'File Explorer', 'value': 'file-explorer', 'icon': 'fa-folder'},
            {'label': 'Data Summary', 'value': 'data-summary', 'icon': 'fa-info-circle'},
            {'label': 'Download Center', 'value': 'download-center', 'icon': 'fa-download'}
        ]
    else:
        return None, current_plot_type
    
    # Reset to monthly-forecast when changing tabs
    new_plot_type = 'monthly-forecast'
    
    if current_tab in ['validation', 'data', 'portfolio']:
        return None, new_plot_type
    
    return [
        dbc.Card([
            dbc.CardBody([
                html.H6("Plot Type", className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [html.I(className=f"fas {btn['icon']} me-2"), btn['label']],
                            id={'type': 'plot-btn', 'index': btn['value']},
                            color="primary" if btn['value'] == new_plot_type else "secondary",
                            outline=btn['value'] != new_plot_type,
                            size="sm",
                            className="w-100"
                        )
                    ], width="auto", className="mb-2") for btn in buttons
                ])
            ], className="py-2")
        ], className="shadow-sm", style={'border': 'none', 'border-radius': '12px'})
    ], new_plot_type

# Callback to update plot type from button clicks
@app.callback(
    Output('current-plot-type', 'data', allow_duplicate=True),
    [Input({'type': 'plot-btn', 'index': ALL}, 'n_clicks')],
    [State('current-plot-type', 'data'),
     State({'type': 'plot-btn', 'index': ALL}, 'id'),
     State('current-tab', 'data')],
    prevent_initial_call=True
)
def update_plot_type_from_click(n_clicks, current_type, button_ids, current_tab):
    try:
        # Don't process if we're in validation, data, or portfolio sections
        if current_tab in ['validation', 'data', 'portfolio']:
            return current_type or 'monthly-forecast'
        
        if not n_clicks or not button_ids or not any(n_clicks):
            return current_type or 'monthly-forecast'
        
        # Find which button was clicked
        for i, clicks in enumerate(n_clicks or []):
            if clicks and i < len(button_ids) and ctx.triggered[0]['prop_id'].startswith(f'{{"index":"{button_ids[i]["index"]}"'):
                return button_ids[i]['index']
        
        return current_type or 'monthly-forecast'
    except Exception:
        return current_type or 'monthly-forecast'

# Main callback for plot type button styling
@app.callback(
    [Output({'type': 'plot-btn', 'index': ALL}, 'color'),
     Output({'type': 'plot-btn', 'index': ALL}, 'outline')],
    [Input('current-plot-type', 'data')],
    [State({'type': 'plot-btn', 'index': ALL}, 'id'),
     State('current-tab', 'data')],
    prevent_initial_call=True
)
def update_plot_type_buttons(current_type, button_ids, current_tab):
    try:
        # Handle case where there are no buttons (validation/data/portfolio sections)
        if not button_ids or len(button_ids) == 0 or current_tab in ['validation', 'data', 'portfolio']:
            return [], []
        
        if not current_type:
            return ['secondary'] * len(button_ids), [True] * len(button_ids)
        
        colors = ['primary' if bid and bid.get('index') == current_type else 'secondary' for bid in button_ids]
        outlines = [bid and bid.get('index') != current_type for bid in button_ids]
        return colors, outlines
    except Exception:
        # Fallback to empty lists to prevent callback errors
        return [], []

# Main content callback
@app.callback(
    Output('main-content', 'children'),
    [Input('current-tab', 'data'),
     Input('current-plot-type', 'data'),
     Input('site-dropdown', 'value'),
     Input('price-type', 'data'),
     Input('revenue-type', 'data'),
     Input('view-mode', 'data')]
)
def update_main_content(current_tab, plot_type, site_name, price_type, revenue_type, view_mode):
    if not site_name and current_tab not in ['validation', 'portfolio']:
        return dbc.Alert("Please select a site to begin analysis", color="info", className="text-center")
    
    if current_tab == 'validation':
        return create_validation_content()
    
    if current_tab == 'data':
        return create_data_view_content(plot_type or 'file-explorer', site_name)
    
    if current_tab == 'portfolio':
        return create_portfolio_content()
    
    # Determine metric based on tab and sub-type
    if current_tab == 'generation':
        metric = 'generation'
    elif current_tab == 'price':
        metric = f'price_{price_type}'
    elif current_tab == 'revenue':
        metric = f'revenue_{revenue_type}'
    else:
        metric = 'generation'
    
    # Create the appropriate plot
    try:
        # Check if this plot type supports historical view
        timeseries_plots = ['daily-forecast', 'monthly-forecast']
        
        if plot_type in timeseries_plots:
            if view_mode == 'historical':
                if plot_type == 'daily-forecast':
                    plot = create_daily_historical(site_name, metric)
                elif plot_type == 'monthly-forecast':
                    plot = create_monthly_historical(site_name, metric)
                else:
                    plot = dbc.Alert("Historical view not available for this plot type", color="warning")
            else:  # forecast mode
                if plot_type == 'daily-forecast':
                    plot = create_daily_forecast(site_name, metric)
                elif plot_type == 'monthly-forecast':
                    plot = create_monthly_forecast(site_name, metric)
                else:
                    plot = dbc.Alert("Please select a plot type", color="warning")
        else:
            # Non-timeseries plots - always forecast mode
            if plot_type == 'diurnal-pattern':
                plot = create_diurnal_pattern(site_name, metric)
            elif plot_type == 'annual-distribution':
                plot = create_annual_distribution(site_name, metric)
            elif plot_type == 'duration-curve':
                plot = create_duration_curve(site_name, metric)
            elif plot_type == 'ghi-hour':
                plot = create_ghi_vs_generation_hour(site_name)
            elif plot_type == 'ghi-temp':
                plot = create_ghi_vs_generation_temp(site_name)
            else:
                plot = dbc.Alert("Please select a plot type", color="warning")
        
        return dbc.Card([
            dbc.CardBody([
                plot
            ])
        ], className="shadow-sm", style={'border': 'none', 'border-radius': '12px'})
        
    except Exception as e:
        return dbc.Alert(f"Error loading plot: {str(e)}", color="danger")

def create_validation_content():
    """Create validation section content"""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className="fas fa-tools fa-4x mb-4", style={'color': '#6c757d', 'opacity': '0.5'}),
                html.H3("Model Validation Tools", className="mb-3"),
                html.P("Advanced validation and backtesting capabilities", className="lead text-muted mb-4"),
                dbc.Badge("COMING SOON", color="info", pill=True, className="fs-5 px-4 py-2"),
                html.Hr(className="my-4"),
                html.H5("Planned Features:", className="mb-3"),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Historical forecast accuracy analysis"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Model performance metrics and KPIs"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Backtesting with confidence intervals"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Scenario analysis and stress testing"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Model comparison and benchmarking"
                    ], className="border-0"),
                ], flush=True, className="bg-transparent")
            ], className="text-center py-5")
        ])
    ], className="shadow-sm", style={'border': 'none', 'border-radius': '12px', 'min-height': '500px'})

def create_data_view_content(view_type, site_name):
    """Create data view content with file explorer, summary, and download options"""
    if not site_name:
        return dbc.Alert("Please select a site to view data", color="info", className="text-center")
    
    if view_type == 'file-explorer':
        return create_file_explorer(site_name)
    elif view_type == 'data-summary':
        return create_data_summary(site_name)
    elif view_type == 'download-center':
        return create_download_center(site_name)
    else:
        return create_file_explorer(site_name)

def create_file_explorer(site_name):
    """Create file explorer view"""
    files_info = dashboard.get_available_files(site_name)
    
    if not files_info:
        return dbc.Alert("No data files found for this site", color="warning", className="text-center")
    
    # Group files by metric type
    grouped_files = {}
    for file_info in files_info:
        metric = file_info['metric']
        if metric not in grouped_files:
            grouped_files[metric] = []
        grouped_files[metric].append(file_info)
    
    cards = []
    for metric, files in grouped_files.items():
        # Create table data
        table_data = []
        for file_info in files:
            table_data.append({
                'Type': file_info['type'].title(),
                'File Name': file_info['file'],
                'Size': file_info['size'],
                'Actions': f"View | Download"
            })
        
        card = dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className=f"fas fa-{get_metric_icon(metric)} me-2"),
                    metric.replace('_', ' ').title()
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dash_table.DataTable(
                    data=table_data,
                    columns=[
                        {'name': 'Type', 'id': 'Type'},
                        {'name': 'File Name', 'id': 'File Name'},
                        {'name': 'Size', 'id': 'Size'},
                        {'name': 'Actions', 'id': 'Actions'}
                    ],
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                    style_data={'backgroundColor': 'white'},
                    page_size=10
                )
            ])
        ], className="mb-3")
        cards.append(card)
    
    return html.Div([
        html.H4(f"Data Files - {dashboard.clean_site_name(site_name)}", className="mb-4"),
        html.Div(cards)
    ])

def create_data_summary(site_name):
    """Create data summary view"""
    files_info = dashboard.get_available_files(site_name)
    
    if not files_info:
        return dbc.Alert("No data files found for this site", color="warning", className="text-center")
    
    # Calculate summary statistics
    total_files = len(files_info)
    metrics = list(set([f['metric'] for f in files_info]))
    file_types = list(set([f['type'] for f in files_info]))
    
    # Create summary cards
    summary_cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(total_files, className="text-primary mb-0"),
                    html.P("Total Files", className="text-muted mb-0")
                ], className="text-center")
            ])
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(len(metrics), className="text-success mb-0"),
                    html.P("Metrics", className="text-muted mb-0")
                ], className="text-center")
            ])
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(len(file_types), className="text-info mb-0"),
                    html.P("Data Types", className="text-muted mb-0")
                ], className="text-center")
            ])
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("PARQUET", className="text-warning mb-0"),
                    html.P("Format", className="text-muted mb-0")
                ], className="text-center")
            ])
        ], md=3)
    ], className="mb-4")
    
    # Create detailed breakdown
    breakdown_data = []
    for metric in metrics:
        metric_files = [f for f in files_info if f['metric'] == metric]
        breakdown_data.append({
            'Metric': metric.replace('_', ' ').title(),
            'Files': len(metric_files),
            'Types': ', '.join(set([f['type'] for f in metric_files]))
        })
    
    return html.Div([
        html.H4(f"Data Summary - {dashboard.clean_site_name(site_name)}", className="mb-4"),
        summary_cards,
        dbc.Card([
            dbc.CardHeader([
                html.H5("Detailed Breakdown", className="mb-0")
            ]),
            dbc.CardBody([
                dash_table.DataTable(
                    data=breakdown_data,
                    columns=[
                        {'name': 'Metric', 'id': 'Metric'},
                        {'name': 'Files', 'id': 'Files'},
                        {'name': 'Types', 'id': 'Types'}
                    ],
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                    style_data={'backgroundColor': 'white'}
                )
            ])
        ])
    ])

def create_download_center(site_name):
    """Create download center view"""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className="fas fa-download fa-4x mb-4", style={'color': '#6c757d', 'opacity': '0.5'}),
                html.H3("Download Center", className="mb-3"),
                html.P("Bulk download capabilities for data files", className="lead text-muted mb-4"),
                dbc.Badge("COMING SOON", color="info", pill=True, className="fs-5 px-4 py-2"),
                html.Hr(className="my-4"),
                html.H5("Planned Features:", className="mb-3"),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Bulk download by metric type"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Custom date range selection"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Multiple format options (PARQUET, CSV, Excel, JSON)"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Compressed archive downloads"
                    ], className="border-0"),
                ], flush=True, className="bg-transparent")
            ], className="text-center py-5")
        ])
    ], className="shadow-sm", style={'border': 'none', 'border-radius': '12px', 'min-height': '500px'})

def get_metric_icon(metric):
    """Get appropriate icon for metric type"""
    icons = {
        'Generation': 'sun',
        'Price_da': 'dollar-sign',
        'Price_rt': 'dollar-sign',
        'Revenue_da': 'chart-line',
        'Revenue_rt': 'chart-line'
    }
    return icons.get(metric, 'file')

def create_portfolio_content():
    """Create portfolio view content"""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className="fas fa-briefcase fa-4x mb-4", style={'color': '#e83e8c', 'opacity': '0.5'}),
                html.H3("Portfolio View", className="mb-3"),
                html.P("Comprehensive portfolio analysis and management tools", className="lead text-muted mb-4"),
                dbc.Badge("COMING SOON", color="info", pill=True, className="fs-5 px-4 py-2"),
                html.Hr(className="my-4"),
                html.H5("Planned Features:", className="mb-3"),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Multi-site portfolio performance dashboard"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Aggregated revenue and generation analytics"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Portfolio optimization recommendations"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Risk assessment and diversification analysis"
                    ], className="border-0"),
                    dbc.ListGroupItem([
                        html.I(className="fas fa-check-circle text-success me-2"),
                        "Comparative site performance metrics"
                    ], className="border-0"),
                ], flush=True, className="bg-transparent")
            ], className="text-center py-5")
        ])
    ], className="shadow-sm", style={'border': 'none', 'border-radius': '12px', 'min-height': '500px'})

# Plot creation functions matching plots.ipynb exactly
def create_clean_layout(fig, title, xaxis_title, yaxis_title, showlegend=True):
    """Apply consistent clean styling to plots based on plots.ipynb"""
    fig.update_layout(
        title={
            'text': title,
            'font': {'size': 16, 'family': 'Inter, sans-serif', 'weight': 600},
            'x': 0.5,
            'xanchor': 'center',
            'y': 0.98,
            'yanchor': 'top'
        },
        xaxis_title={
            'text': xaxis_title,
            'font': {'size': 12, 'family': 'Inter, sans-serif'}
        },
        yaxis_title={
            'text': yaxis_title,
            'font': {'size': 12, 'family': 'Inter, sans-serif'}
        },
        hovermode='x unified',
        template='none',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=700,
        showlegend=showlegend,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255,255,255,0)',
            bordercolor='rgba(255,255,255,0)',
            font=dict(size=11, family='Inter, sans-serif')
        ),
        margin=dict(l=60, r=20, t=60, b=80),
        font=dict(family="Inter, sans-serif", size=11, color=COLORS['text'])
    )
    
    # Remove gridlines and clean up axes like plots.ipynb
    fig.update_xaxes(
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor='lightgray',
        zeroline=False,
        tickfont=dict(size=10)
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128,128,128,0.2)',
        showline=True,
        linewidth=1,
        linecolor='lightgray',
        zeroline=False,
        tickfont=dict(size=10)
    )
    
    return fig

def create_daily_forecast(site_name, metric):
    """Create daily forecast plot with P10-P90 bands matching ipynb"""
    dist_file = dashboard.find_distribution_file(site_name, metric, 'daily')
    if not dist_file:
        return dbc.Alert("No daily forecast data available", color="warning", className="text-center")
    
    try:
        # Read parquet file instead of csv
        df = pd.read_parquet(dist_file)
        
        fig = go.Figure()
        
        # Add P10-P90 band (matching ipynb)
        fig.add_trace(go.Scatter(
            x=list(range(len(df))) + list(range(len(df)-1, -1, -1)),
            y=list(df['p10']) + list(df['p90'][::-1]),
            fill='toself',
            fillcolor=f'rgba({int(COLORS[metric][1:3], 16)}, {int(COLORS[metric][3:5], 16)}, {int(COLORS[metric][5:7], 16)}, 0.3)',
            line=dict(color='rgba(255,255,255,0)'),
            name='P10-P90 Band',
            showlegend=True
        ))
        
        # Add mean line
        fig.add_trace(go.Scatter(
            x=list(range(len(df))),
            y=df['mean'],
            mode='lines',
            name='Mean',
            line=dict(color=COLORS[metric], width=2.5)
        ))
        
        # Format x-axis - show every 30th day
        tick_positions = list(range(0, len(df), 30))
        tick_labels = []
        for i in tick_positions:
            month = int(df.iloc[i]['month'])
            day = int(df.iloc[i]['day'])
            tick_labels.append(f"{MONTH_NAMES[month-1][:3]} {day}")
        
        # Title and labels based on metric
        if metric == 'generation':
            title = f'Daily Generation Forecast - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Generation (MWh)'
            yaxis_format = ',.0f'
        elif metric in ['price_da', 'price_rt']:
            price_type = 'Day-Ahead' if metric == 'price_da' else 'Real-Time'
            title = f'Daily {price_type} Price Forecast - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Price ($/MWh)'
            yaxis_format = '$,.0f'
        else:  # revenue
            revenue_type = 'Day-Ahead' if metric == 'revenue_da' else 'Real-Time'
            title = f'Daily {revenue_type} Revenue Forecast - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Revenue ($)'
            yaxis_format = '$,.0f'
        
        fig = create_clean_layout(fig, title, '', yaxis_title)
        
        # Custom x-axis for daily data
        fig.update_xaxes(
            tickmode='array',
            tickvals=tick_positions,
            ticktext=tick_labels,
            tickangle=-45
        )
        
        # Format y-axis
        fig.update_yaxes(tickformat=yaxis_format)
        
        return html.Div([
            dbc.Button(
                html.I(className="fas fa-arrow-left"),
                id={'type': 'daily-view-nav-btn', 'action': 'to-historical'},
                color="primary",
                size="sm",
                className="position-absolute",
                style={
                    'top': '50%',
                    'left': '60px',  # Padding from y-axis
                    'transform': 'translateY(-50%)',
                    'zIndex': '1000',
                    'borderRadius': '50%',
                    'width': '40px',
                    'height': '40px'
                }
            ),
            dbc.Tooltip("View Historical Data", target={'type': 'daily-view-nav-btn', 'action': 'to-historical'}),
            dcc.Graph(figure=fig, config={'displayModeBar': False})
        ], style={'position': 'relative'})
        
    except Exception as e:
        return dbc.Alert(f"Error in daily forecast: {str(e)}", color="danger")

def create_daily_historical(site_name, metric):
    """Create daily historical plot using historical data as continuous timeseries"""
    hist_file = dashboard.find_historical_file(site_name, metric, 'daily')
    if not hist_file:
        return dbc.Alert("No daily historical data available", color="warning", className="text-center")
    
    try:
        # Read parquet file instead of csv
        df = pd.read_parquet(hist_file)
        
        # Get the column name for the metric
        if metric == 'generation':
            value_col = 'daily_generation_mwh'
        elif metric in ['price_da', 'price_rt']:
            value_col = 'weighted_price'
        elif metric in ['revenue_da', 'revenue_rt']:
            value_col = metric
        else:
            return dbc.Alert("Unsupported metric for historical view", color="warning")
        
        if value_col not in df.columns:
            return dbc.Alert(f"Column {value_col} not found in historical data", color="warning")
        
        # Get last 10 years of data
        years = sorted(df['year'].unique())
        if len(years) >= 10:
            recent_years = years[-10:]
        else:
            recent_years = years
        
        df_recent = df[df['year'].isin(recent_years)].copy()
        
        if isinstance(df_recent, pd.DataFrame):
            # Create continuous date column
            df_recent['date'] = pd.to_datetime(df_recent[['year', 'month', 'day']])
            df_recent = df_recent.sort_values('date')
            
            # Remove any missing values
            df_recent = df_recent.dropna(subset=[value_col])
        
        fig = go.Figure()
        
        # Add single continuous line with markers (similar to monthly)
        fig.add_trace(go.Scatter(
            x=df_recent['date'],
            y=df_recent[value_col],
            mode='lines',
            name='Historical Data',
            line=dict(color=COLORS[metric], width=2)
        ))
        
        # Title and labels based on metric
        if metric == 'generation':
            title = f'Daily Generation Historical - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Generation (MWh)'
            yaxis_format = ',.0f'
        elif metric in ['price_da', 'price_rt']:
            price_type = 'Day-Ahead' if metric == 'price_da' else 'Real-Time'
            title = f'Daily {price_type} Price Historical - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Price ($/MWh)'
            yaxis_format = '$,.0f'
        else:  # revenue
            revenue_type = 'Day-Ahead' if metric == 'revenue_da' else 'Real-Time'
            title = f'Daily {revenue_type} Revenue Historical - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Revenue ($)'
            yaxis_format = '$,.0f'
        
        fig = create_clean_layout(fig, title, 'Date', yaxis_title)
        
        # Format y-axis
        fig.update_yaxes(tickformat=yaxis_format)
        
        return html.Div([
            dbc.Button(
                html.I(className="fas fa-arrow-right"),
                id={'type': 'daily-view-nav-btn', 'action': 'to-forecast'},
                color="success",
                size="sm",
                className="position-absolute",
                style={
                    'top': '50%',
                    'right': '60px',  # Padding from y-axis
                    'transform': 'translateY(-50%)',
                    'zIndex': '1000',
                    'borderRadius': '50%',
                    'width': '40px',
                    'height': '40px'
                }
            ),
            dbc.Tooltip("View Forecast Data", target={'type': 'daily-view-nav-btn', 'action': 'to-forecast'}),
            dcc.Graph(figure=fig, config={'displayModeBar': False})
        ], style={'position': 'relative'})
        
    except Exception as e:
        return dbc.Alert(f"Error in daily historical: {str(e)}", color="danger")

def create_monthly_historical(site_name, metric):
    """Create monthly historical plot using historical data as continuous timeseries"""
    hist_file = dashboard.find_historical_file(site_name, metric, 'monthly')
    if not hist_file:
        return dbc.Alert("No monthly historical data available", color="warning", className="text-center")
    
    try:
        # Read parquet file instead of csv
        df = pd.read_parquet(hist_file)
        
        # Get the column name for the metric
        if metric == 'generation':
            value_col = 'monthly_generation_mwh'
        elif metric in ['price_da', 'price_rt']:
            value_col = 'weighted_price'
        elif metric in ['revenue_da', 'revenue_rt']:
            value_col = metric
        else:
            return dbc.Alert("Unsupported metric for historical view", color="warning")
        
        if value_col not in df.columns:
            return dbc.Alert(f"Column {value_col} not found in historical data", color="warning")
        
        # Get last 10 years of data
        years = sorted(df['year'].unique())
        if len(years) >= 10:
            recent_years = years[-10:]
        else:
            recent_years = years
        
        df_recent = df[df['year'].isin(recent_years)].copy()
        
        if isinstance(df_recent, pd.DataFrame):
            # Create continuous date column (first day of each month)
            df_recent['date'] = pd.to_datetime(df_recent[['year', 'month']].assign(day=1))
            df_recent = df_recent.sort_values('date')
            
            # Remove any missing values
            df_recent = df_recent.dropna(subset=[value_col])
        
        fig = go.Figure()
        
        # Add single continuous line
        fig.add_trace(go.Scatter(
            x=df_recent['date'],
            y=df_recent[value_col],
            mode='lines+markers',
            name='Historical Data',
            line=dict(color=COLORS[metric], width=2),
            marker=dict(size=4)
        ))
        
        # Title and labels based on metric
        if metric == 'generation':
            title = f'Monthly Generation Historical - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Generation (MWh)'
            yaxis_format = ',.0f'
        elif metric in ['price_da', 'price_rt']:
            price_type = 'Day-Ahead' if metric == 'price_da' else 'Real-Time'
            title = f'Monthly {price_type} Price Historical - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Price ($/MWh)'
            yaxis_format = '$,.0f'
        else:  # revenue
            revenue_type = 'Day-Ahead' if metric == 'revenue_da' else 'Real-Time'
            title = f'Monthly {revenue_type} Revenue Historical - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Revenue ($)'
            yaxis_format = '$,.0f'
        
        fig = create_clean_layout(fig, title, 'Date', yaxis_title)
        
        # Format y-axis
        fig.update_yaxes(tickformat=yaxis_format)
        
        return html.Div([
            dbc.Button(
                html.I(className="fas fa-arrow-right"),
                id={'type': 'view-nav-btn', 'action': 'to-forecast'},
                color="success",
                size="sm",
                className="position-absolute",
                style={
                    'top': '50%',
                    'right': '60px',  # Padding from y-axis
                    'transform': 'translateY(-50%)',
                    'zIndex': '1000',
                    'borderRadius': '50%',
                    'width': '40px',
                    'height': '40px'
                }
            ),
            dbc.Tooltip("View Forecast Data", target={'type': 'view-nav-btn', 'action': 'to-forecast'}),
            dcc.Graph(figure=fig, config={'displayModeBar': False})
        ], style={'position': 'relative'})
        
    except Exception as e:
        return dbc.Alert(f"Error in monthly historical: {str(e)}", color="danger")

def create_monthly_forecast(site_name, metric):
    """Create monthly forecast plot with P10-P90 bands, paths, and historical average"""
    dist_file = dashboard.find_distribution_file(site_name, metric, 'monthly')
    ts_file = dashboard.find_timeseries_file(site_name, metric, 'monthly')
    
    if not dist_file:
        # Provide more detailed error message
        error_msg = f"No monthly forecast data available for {metric} at {site_name}"
        print(f"❌ {error_msg}")
        print(f"   Looking for file pattern: {site_name}_{metric}_monthly_distribution.parquet")
        print(f"   In folder: {dashboard.portfolio_path / site_name}")
        return dbc.Alert(error_msg, color="warning", className="text-center")
    
    try:
        # Read parquet files instead of csv
        df_dist = pd.read_parquet(dist_file)
        
        # Calculate historical average
        hist_avg = dashboard.calculate_historical_average(site_name, metric, 'monthly')
        
        # Determine months
        if 'month' in df_dist.columns:
            actual_months = df_dist['month'].values
            x = list(range(len(actual_months)))
            month_labels = [MONTH_NAMES[int(m)-1][:3] for m in actual_months]
        else:
            x = list(range(12))
            month_labels = [m[:3] for m in MONTH_NAMES]
        
        fig = go.Figure()
        
        # Add paths if available (limit for performance)
        if ts_file and Path(ts_file).exists():
            df_ts = pd.read_parquet(ts_file)
            path_cols = [col for col in df_ts.columns if col.startswith('path_')]
            for i, path in enumerate(path_cols[:30]):  # Limit to 30 paths
                fig.add_trace(go.Scatter(
                    x=x,
                    y=df_ts[path],
                    mode='lines',
                    line=dict(color=COLORS[metric], width=0.5),
                    opacity=0.1,
                    showlegend=False,
                    hoverinfo='skip'
                ))
        
        # Add P10-P90 band
        fig.add_trace(go.Scatter(
            x=x + x[::-1],
            y=list(df_dist['p10']) + list(df_dist['p90'][::-1]),
            fill='toself',
            fillcolor=f'rgba({int(COLORS[metric][1:3], 16)}, {int(COLORS[metric][3:5], 16)}, {int(COLORS[metric][5:7], 16)}, 0.3)',
            line=dict(color='rgba(255,255,255,0)'),
            name='P10-P90 Band',
            showlegend=True
        ))
        
        # Add mean line
        fig.add_trace(go.Scatter(
            x=x,
            y=df_dist['mean'],
            mode='lines+markers',
            name='Forecast Mean',
            line=dict(color=COLORS[metric], width=3),
            marker=dict(size=6)
        ))
        
        # Plot historical average if available
        if hist_avg is not None and isinstance(hist_avg, pd.DataFrame) and 'month' in df_dist.columns:
            hist_values = []
            for month in actual_months:
                hist_subset = hist_avg[hist_avg['month'] == month]
                if len(hist_subset) > 0:
                    hist_values.append(hist_subset['historical_avg'].iloc[0])
                else:
                    hist_values.append(np.nan)
            
            fig.add_trace(go.Scatter(
                x=x,
                y=hist_values,
                mode='lines+markers',
                name='10-Year Historical Avg',
                line=dict(color=COLORS['historical'], width=3, dash='dash'),
                marker=dict(size=6, symbol='square')
            ))
        
        # Title and labels
        if metric == 'generation':
            title = f'Monthly Generation Forecast - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Generation (MWh)'
            yaxis_format = ',.0f'
        elif metric in ['price_da', 'price_rt']:
            price_type = 'Day-Ahead' if metric == 'price_da' else 'Real-Time'
            title = f'Monthly {price_type} Price Forecast - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Price ($/MWh)'
            yaxis_format = '$,.0f'
        else:  # revenue
            revenue_type = 'Day-Ahead' if metric == 'revenue_da' else 'Real-Time'
            title = f'Monthly {revenue_type} Revenue Forecast - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Revenue ($)'
            yaxis_format = '$,.0f'
        
        fig = create_clean_layout(fig, title, '', yaxis_title)
        
        # Custom x-axis for monthly data
        fig.update_xaxes(
            tickmode='array',
            tickvals=x,
            ticktext=month_labels
        )
        
        # Format y-axis
        fig.update_yaxes(tickformat=yaxis_format)
        
        return html.Div([
            dbc.Button(
                html.I(className="fas fa-arrow-left"),
                id={'type': 'view-nav-btn', 'action': 'to-historical'},
                color="primary",
                size="sm",
                className="position-absolute",
                style={
                    'top': '50%',
                    'left': '60px',  # Padding from y-axis
                    'transform': 'translateY(-50%)',
                    'zIndex': '1000',
                    'borderRadius': '50%',
                    'width': '40px',
                    'height': '40px'
                }
            ),
            dbc.Tooltip("View Historical Data", target={'type': 'view-nav-btn', 'action': 'to-historical'}),
            dcc.Graph(figure=fig, config={'displayModeBar': False})
        ], style={'position': 'relative'})
        
    except Exception as e:
        return dbc.Alert(f"Error in monthly forecast: {str(e)}", color="danger")

def create_diurnal_pattern(site_name, metric):
    """Create diurnal pattern plot with P5-P95 band and historical average"""
    dist_file = dashboard.find_distribution_file(site_name, metric, 'hourly')
    if not dist_file:
        return dbc.Alert("No hourly data available", color="warning", className="text-center")
    
    try:
        # Read parquet file instead of csv
        df = pd.read_parquet(dist_file)
        
        # Calculate historical average
        hist_avg = dashboard.calculate_historical_average(site_name, metric, 'hourly')
        
        # Group by hour
        hourly = df.groupby('hour').agg({
            'mean': 'mean',
            'p5': 'mean',
            'p95': 'mean'
        }).reset_index()
        
        fig = go.Figure()
        
        # Add P5-P95 band
        fig.add_trace(go.Scatter(
            x=list(hourly['hour']) + list(hourly['hour'][::-1]),
            y=list(hourly['p95']) + list(hourly['p5'][::-1]),
            fill='toself',
            fillcolor=f'rgba({int(COLORS[metric][1:3], 16)}, {int(COLORS[metric][3:5], 16)}, {int(COLORS[metric][5:7], 16)}, 0.3)',
            line=dict(color='rgba(255,255,255,0)'),
            name='P5-P95 Band',
            showlegend=True
        ))
        
        # Add mean line
        fig.add_trace(go.Scatter(
            x=hourly['hour'],
            y=hourly['mean'],
            mode='lines+markers',
            name='Forecast Mean',
            line=dict(color=COLORS[metric], width=3),
            marker=dict(size=6)
        ))
        
        # Plot historical average if available
        if hist_avg is not None:
            fig.add_trace(go.Scatter(
                x=hist_avg['hour'],
                y=hist_avg['historical_avg'],
                mode='lines+markers',
                name='5-Year Historical Avg',
                line=dict(color=COLORS['historical'], width=3, dash='dash'),
                marker=dict(size=6, symbol='square')
            ))
        
        # Title and labels
        if metric == 'generation':
            title = f'Generation Diurnal Pattern - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Generation (MW)'
            yaxis_format = ',.0f'
        elif metric in ['price_da', 'price_rt']:
            price_type = 'Day-Ahead' if metric == 'price_da' else 'Real-Time'
            title = f'{price_type} Price Diurnal Pattern - {dashboard.clean_site_name(site_name)}'
            yaxis_title = 'Price ($/MWh)'
            yaxis_format = '$,.0f'
        
        fig = create_clean_layout(fig, title, 'Hour of Day', yaxis_title)
        
        # Custom x-axis for hourly data
        fig.update_xaxes(
            tickmode='linear',
            tick0=0,
            dtick=2,
            range=[-0.5, 23.5]
        )
        
        # Format y-axis
        fig.update_yaxes(tickformat=yaxis_format)
        
        return dcc.Graph(figure=fig, config={'displayModeBar': False})
        
    except Exception as e:
        return dbc.Alert(f"Error in diurnal pattern: {str(e)}", color="danger")

def create_annual_distribution(site_name, metric):
    """Create annual distribution plot with KDE and statistics"""
    ts_file = dashboard.find_timeseries_file(site_name, metric, 'monthly')
    if not ts_file:
        return dbc.Alert("No monthly timeseries data available", color="warning", className="text-center")
    
    try:
        # Read parquet file instead of csv
        df = pd.read_parquet(ts_file)
        
        # Get all columns (historical + paths)
        year_cols = [col for col in df.columns if str(col).isdigit() and 1980 <= int(col) <= 2024]
        path_cols = [col for col in df.columns if col.startswith('path_')]
        all_cols = year_cols + path_cols
        
        # Calculate annual totals
        annual_values = []
        for col in all_cols:
            if df[col].notna().sum() == 12:  # Only complete years
                annual_values.append(df[col].sum())
        
        if not annual_values:
            return dbc.Alert("Insufficient data for annual distribution", color="warning", className="text-center")
        
        annual_values = np.array(annual_values)
        
        # Statistics
        mean_val = np.mean(annual_values)
        p5_val = np.percentile(annual_values, 5)
        p95_val = np.percentile(annual_values, 95)
        std_val = np.std(annual_values)
        cv = (std_val / mean_val) * 100
        
        # Create KDE for smooth distribution
        x_min = annual_values.min() - 0.1 * (annual_values.max() - annual_values.min())
        x_max = annual_values.max() + 0.1 * (annual_values.max() - annual_values.min())
        x_smooth = np.linspace(x_min, x_max, 300)
        kde = gaussian_kde(annual_values, bw_method='scott')
        kde_values = kde(x_smooth) * 100  # Convert to percentage
        
        fig = go.Figure()
        
        # Add KDE curve
        fig.add_trace(go.Scatter(
            x=x_smooth,
            y=kde_values,
            mode='lines',
            fill='tozeroy',
            fillcolor=f'rgba({int(COLORS[metric][1:3], 16)}, {int(COLORS[metric][3:5], 16)}, {int(COLORS[metric][5:7], 16)}, 0.3)',
            line=dict(color=COLORS[metric], width=3),
            name='Distribution'
        ))
        
        # Add vertical lines for statistics
        fig.add_vline(x=mean_val, line_dash="dash", line_color="red", line_width=2,
                      annotation_text=f"Mean: {mean_val:,.0f}", annotation_position="top right")
        fig.add_vline(x=p5_val, line_dash="dot", line_color="darkgreen", line_width=2,
                      annotation_text=f"P5: {p5_val:,.0f}", annotation_position="top left")
        fig.add_vline(x=p95_val, line_dash="dot", line_color="darkgreen", line_width=2,
                      annotation_text=f"P95: {p95_val:,.0f}", annotation_position="top right")
        
        # Title and labels
        if metric == 'generation':
            title = f'Generation Annual Distribution - {dashboard.clean_site_name(site_name)}'
            xaxis_title = 'Annual Generation (MWh)'
            xaxis_format = ',.0f'
        elif metric in ['revenue_da', 'revenue_rt']:
            revenue_type = 'Day-Ahead' if metric == 'revenue_da' else 'Real-Time'
            title = f'{revenue_type} Revenue Annual Distribution - {dashboard.clean_site_name(site_name)}'
            xaxis_title = 'Annual Revenue ($)'
            xaxis_format = '$,.0f'
        
        fig = create_clean_layout(fig, title, xaxis_title, 'Probability Density (%)', showlegend=False)
        
        # Format x-axis
        fig.update_xaxes(tickformat=xaxis_format)
        
        # Add statistics box
        stats_text = f'n = {len(annual_values)}<br>Std Dev: {std_val:,.0f}<br>CV: {cv:.1f}%'
        
        fig.add_annotation(
            text=stats_text,
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=10),
            align="left",
            bordercolor="gray",
            borderwidth=1,
            borderpad=10,
            bgcolor="white",
            opacity=0.8
        )
        
        return dcc.Graph(figure=fig, config={'displayModeBar': False})
        
    except Exception as e:
        return dbc.Alert(f"Error in annual distribution: {str(e)}", color="danger")

def create_duration_curve(site_name, metric):
    """Create duration curve for prices"""
    ts_file = dashboard.find_timeseries_file(site_name, metric, 'hourly')
    if not ts_file:
        return dbc.Alert("No hourly timeseries data available", color="warning", className="text-center")
    
    try:
        # Read parquet file instead of csv
        df = pd.read_parquet(ts_file)
        
        # Get all columns
        year_cols = [col for col in df.columns if str(col).isdigit() and 1980 <= int(col) <= 2024]
        path_cols = [col for col in df.columns if col.startswith('path_')]
        all_cols = year_cols + path_cols
        
        # Collect all values
        all_values = []
        for col in all_cols:
            col_values = pd.to_numeric(df[col], errors='coerce')
            if isinstance(col_values, pd.Series):
                col_values = col_values.dropna()
                all_values.extend(col_values.tolist())
        
        if not all_values:
            return dbc.Alert("Insufficient data for duration curve", color="warning", className="text-center")
        
        # Sort for duration curve
        sorted_values = np.sort(all_values)[::-1]
        n_values = len(sorted_values)
        duration_pct = np.linspace(0, 100, n_values)
        
        # Calculate key percentiles
        mean_value = np.mean(all_values)
        p10_val = np.percentile(all_values, 90)  # Note: reversed for duration curve
        p50_val = np.percentile(all_values, 50)
        p90_val = np.percentile(all_values, 10)
        
        fig = go.Figure()
        
        # Add duration curve
        fig.add_trace(go.Scatter(
            x=duration_pct,
            y=sorted_values,
            mode='lines',
            name='Duration Curve',
            line=dict(color=COLORS[metric], width=2.5)
        ))
        
        # Add mean line
        fig.add_hline(y=mean_value, line_dash="dash", line_color="red", line_width=2,
                      annotation_text=f"Mean: ${mean_value:.2f}", annotation_position="right")
        
        # Mark key percentiles
        percentiles = [(10, p10_val), (50, p50_val), (90, p90_val)]
        for pct, val in percentiles:
            idx = np.argmin(np.abs(sorted_values - val))
            fig.add_trace(go.Scatter(
                x=[duration_pct[idx]],
                y=[val],
                mode='markers+text',
                marker=dict(size=8, color='darkblue'),
                text=[f'P{pct}: ${val:.0f}'],
                textposition='top center',
                showlegend=False
            ))
        
        # Add zero line if negative prices
        if min(sorted_values) < 0:
            fig.add_hline(y=0, line_color="gray", line_width=1, opacity=0.5)
        
        # Title
        price_type = 'Day-Ahead' if metric == 'price_da' else 'Real-Time'
        title = f'{price_type} Price Duration Curve - {dashboard.clean_site_name(site_name)}'
        
        fig = create_clean_layout(fig, title, 'Duration (% of time)', 'Price ($/MWh)', showlegend=False)
        
        # Format axes
        fig.update_xaxes(range=[0, 100])
        fig.update_yaxes(tickformat='$,.0f')
        
        return dcc.Graph(figure=fig, config={'displayModeBar': False})
        
    except Exception as e:
        return dbc.Alert(f"Error in duration curve: {str(e)}", color="danger")

def create_ghi_vs_generation_hour(site_name):
    """Create GHI vs Generation colored by hour"""
    hist_file = dashboard.find_historical_file(site_name)
    if not hist_file:
        return dbc.Alert("No historical data available", color="warning", className="text-center")
    
    try:
        # Read parquet file instead of csv
        df = pd.read_parquet(hist_file)
        
        # Parse dates and get complete years
        df['date'] = pd.to_datetime(df['datetime'] if 'datetime' in df.columns else 
                                  df[['year', 'month', 'day', 'hour']])
        
        year_counts = df.groupby('year').size()
        complete_years = year_counts[year_counts >= 8760].index.tolist()
        
        if not complete_years:
            return dbc.Alert("No complete years of data available", color="warning", className="text-center")
        
        # Use last 10 complete years
        years_to_use = sorted(complete_years)[-10:]
        df_years = df[df['year'].isin(years_to_use)].copy()
        
        # Filter data
        df_filtered = df_years[(df_years['generation_mw'] > 0.1) & 
                              (df_years['shortwave_radiation'] > 0)].copy()
        
        if len(df_filtered) < 100:
            return dbc.Alert("Insufficient data for analysis", color="warning", className="text-center")
        
        # Sample data if too large
        if len(df_filtered) > 10000:
            df_filtered = df_filtered.sample(n=10000, random_state=42)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_filtered['shortwave_radiation'],
            y=df_filtered['generation_mw'],
            mode='markers',
            marker=dict(
                size=4,
                color=df_filtered['hour'],
                colorscale='Viridis',
                colorbar=dict(
                    title="Hour of Day",
                    titleside="right",
                    tickmode="linear",
                    tick0=0,
                    dtick=4
                ),
                opacity=0.7
            ),
            text=[f"Hour: {h}<br>GHI: {g:.0f} W/m²<br>Gen: {gen:.2f} MW" 
                  for h, g, gen in zip(df_filtered['hour'], 
                                       df_filtered['shortwave_radiation'],
                                       df_filtered['generation_mw'])],
            hoverinfo='text'
        ))
        
        years_str = f"{min(years_to_use)}-{max(years_to_use)}" if len(years_to_use) > 1 else str(years_to_use[0])
        title = f'Generation vs GHI by Hour - {dashboard.clean_site_name(site_name)} ({years_str})'
        
        fig = create_clean_layout(fig, title, 'Global Horizontal Irradiance (W/m²)', 'Generation (MW)', showlegend=False)
        
        # Add metadata box
        fig.add_annotation(
            text=f'Years: {years_str}<br>Data Points: {len(df_filtered):,}<br>Max Generation: {df_filtered["generation_mw"].max():.2f} MW<br>Max GHI: {df_filtered["shortwave_radiation"].max():.1f} W/m²',
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=10),
            align="left",
            bordercolor="gray",
            borderwidth=1,
            borderpad=10,
            bgcolor="white",
            opacity=0.8
        )
        
        return dcc.Graph(figure=fig, config={'displayModeBar': False})
        
    except Exception as e:
        return dbc.Alert(f"Error in GHI vs generation (hour): {str(e)}", color="danger")

def create_ghi_vs_generation_temp(site_name):
    """Create GHI vs Generation colored by temperature"""
    hist_file = dashboard.find_historical_file(site_name)
    if not hist_file:
        return dbc.Alert("No historical data available", color="warning", className="text-center")
    
    try:
        # Read parquet file instead of csv
        df = pd.read_parquet(hist_file)
        
        # Parse dates and get complete years
        df['date'] = pd.to_datetime(df['datetime'] if 'datetime' in df.columns else 
                                  df[['year', 'month', 'day', 'hour']])
        
        year_counts = df.groupby('year').size()
        complete_years = year_counts[year_counts >= 8760].index.tolist()
        
        if not complete_years:
            return dbc.Alert("No complete years of data available", color="warning", className="text-center")
        
        # Use last 5 complete years
        years_to_use = sorted(complete_years)[-5:]
        df_years = df[df['year'].isin(years_to_use)].copy()
        
        # Filter data
        df_filtered = df_years[(df_years['generation_mw'] > 0.1) & 
                              (df_years['shortwave_radiation'] > 0)].copy()
        
        if len(df_filtered) < 100:
            return dbc.Alert("Insufficient data for analysis", color="warning", className="text-center")
        
        # Sample data if too large
        if len(df_filtered) > 10000:
            df_filtered = df_filtered.sample(n=10000, random_state=42)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_filtered['shortwave_radiation'],
            y=df_filtered['generation_mw'],
            mode='markers',
            marker=dict(
                size=4,
                color=df_filtered['temperature_2m'],
                colorscale='RdBu_r',
                colorbar=dict(
                    title="Temperature (°C)",
                    titleside="right"
                ),
                opacity=0.7
            ),
            text=[f"Temp: {t:.1f}°C<br>GHI: {g:.0f} W/m²<br>Gen: {gen:.2f} MW" 
                  for t, g, gen in zip(df_filtered['temperature_2m'], 
                                       df_filtered['shortwave_radiation'],
                                       df_filtered['generation_mw'])],
            hoverinfo='text'
        ))
        
        years_str = f"{min(years_to_use)}-{max(years_to_use)}" if len(years_to_use) > 1 else str(years_to_use[0])
        title = f'{dashboard.clean_site_name(site_name)} ({years_str})<br>Modeled Generation vs. GHI (Colored by Temperature)'
        
        fig = create_clean_layout(fig, title, 'Global Horizontal Irradiance (W/m²)', 'Modeled Solar Generation (MW)', showlegend=False)
        
        # Add metadata box
        fig.add_annotation(
            text=f'Years: {years_str}<br>Data Points: {len(df_filtered):,}<br>Max Generation: {df_filtered["generation_mw"].max():.2f} MW<br>Temp Range: {df_filtered["temperature_2m"].min():.1f}°C - {df_filtered["temperature_2m"].max():.1f}°C',
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=10),
            align="left",
            bordercolor="gray",
            borderwidth=1,
            borderpad=10,
            bgcolor="white",
            opacity=0.8
        )
        
        return dcc.Graph(figure=fig, config={'displayModeBar': False})
        
    except Exception as e:
        return dbc.Alert(f"Error in GHI vs generation (temp): {str(e)}", color="danger")

# Navigation callbacks for historical/forecast view switching
@app.callback(
    Output('view-mode', 'data'),
    [Input({'type': 'view-nav-btn', 'action': ALL}, 'n_clicks'),
     Input({'type': 'daily-view-nav-btn', 'action': ALL}, 'n_clicks')],
    State('view-mode', 'data'),
    prevent_initial_call=True
)
def toggle_view_mode(monthly_clicks, daily_clicks, current_mode):
    if not any(monthly_clicks or []) and not any(daily_clicks or []):
        return current_mode
    
    triggered = ctx.triggered_id
    
    if triggered and triggered.get('action') == 'to-historical':
        return 'historical'
    elif triggered and triggered.get('action') == 'to-forecast':
        return 'forecast'
    
    return current_mode

# Suggestion Box Callbacks
@app.callback(
    [Output('suggestion-modal', 'is_open'),
     Output('suggestion-context', 'value')],
    [Input('suggestion-btn', 'n_clicks'),
     Input('suggestion-cancel', 'n_clicks'),
     Input('suggestion-submit', 'n_clicks')],
    [State('suggestion-modal', 'is_open'),
     State('current-tab', 'data'),
     State('current-plot-type', 'data'),
     State('site-dropdown', 'value'),
     State('price-type', 'data'),
     State('revenue-type', 'data')]
)
def toggle_suggestion_modal(btn_clicks, cancel_clicks, submit_clicks, is_open, 
                           current_tab, plot_type, site_name, price_type, revenue_type):
    triggered = ctx.triggered_id
    
    if triggered == 'suggestion-btn':
        # Create context string
        context_parts = []
        if site_name:
            context_parts.append(f"Site: {dashboard.clean_site_name(site_name)}")
        
        if current_tab:
            tab_name = current_tab.title()
            if current_tab == 'price':
                tab_name += f" ({price_type.upper()})"
            elif current_tab == 'revenue':
                tab_name += f" ({revenue_type.upper()})"
            context_parts.append(f"Section: {tab_name}")
        
        if plot_type and current_tab not in ['validation', 'data']:
            context_parts.append(f"View: {plot_type.replace('-', ' ').title()}")
        
        context_str = " | ".join(context_parts)
        return True, context_str
    
    elif triggered in ['suggestion-cancel', 'suggestion-submit']:
        return False, ""
    
    return is_open, ""

@app.callback(
    [Output('suggestion-toast', 'is_open'),
     Output('suggestion-name', 'value'),
     Output('suggestion-email', 'value'),
     Output('suggestion-text', 'value'),
     Output('suggestion-priority', 'value')],
    [Input('suggestion-submit', 'n_clicks')],
    [State('suggestion-name', 'value'),
     State('suggestion-email', 'value'),
     State('suggestion-text', 'value'),
     State('suggestion-priority', 'value'),
     State('suggestion-context', 'value')],
    prevent_initial_call=True
)
def submit_suggestion(n_clicks, name, email, suggestion_text, priority, context):
    if n_clicks:
        import datetime
        import csv
        import os
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        suggestion_data = {
            'timestamp': timestamp,
            'name': name or 'Anonymous',
            'email': email or 'Not provided',
            'context': context,
            'suggestion': suggestion_text,
            'priority': priority
        }
        
        # Print to console
        print("=" * 50)
        print("NEW SUGGESTION RECEIVED")
        print("=" * 50)
        for key, value in suggestion_data.items():
            print(f"{key.title()}: {value}")
        print("=" * 50)
        
        # Save to CSV file
        csv_filename = 'suggestions.csv'
        file_exists = os.path.isfile(csv_filename)
        
        try:
            with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'name', 'email', 'context', 'suggestion', 'priority']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                
                # Write suggestion data
                writer.writerow(suggestion_data)
                
            print(f"✅ Suggestion saved to {csv_filename}")
            
        except Exception as e:
            print(f"❌ Error saving suggestion to CSV: {str(e)}")
        
        # Clear form and show toast
        return True, "", "", "", "medium"
    
    return False, name, email, suggestion_text, priority

# Reset view mode to forecast when changing tabs
@app.callback(
    Output('view-mode', 'data', allow_duplicate=True),
    [Input('current-tab', 'data'),
     Input('current-plot-type', 'data')],
    prevent_initial_call=True
)
def reset_view_mode(current_tab, plot_type):
    return 'forecast'

# Expose server for production deployment
server = app.server

# Run the app
if __name__ == '__main__':
    import os
    
    # Get environment settings
    debug = os.environ.get('DASH_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 8050))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("🚀 Starting Renewable Portfolio Dashboard (Parquet Version)...")
    print("📁 Looking for folder: 'Renewable Portfolio LLC_parquet' (with underscore)")
    
    if debug:
        print("📍 Running in debug mode")
        print(f"📍 Visit http://127.0.0.1:{port} in your browser")
    else:
        print("📍 Running in production mode")
    
    app.run(debug=debug, port=port, host=host)