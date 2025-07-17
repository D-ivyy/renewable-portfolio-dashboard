# Renewable Portfolio Analytics Dashboard

A comprehensive Dash-based web application for analyzing renewable energy portfolio data including generation forecasts, pricing, and revenue analytics.

## Features

- **Generation Analysis**: Daily, monthly forecasts with historical comparisons
- **Price Analytics**: Day-ahead and real-time pricing with duration curves
- **Revenue Forecasting**: Comprehensive revenue analysis and distributions
- **Interactive Dashboards**: Modern, responsive interface with Bootstrap styling
- **Data Validation**: Model validation and backtesting capabilities (coming soon)
- **Portfolio Overview**: Multi-site portfolio analysis (coming soon)

## Quick Start

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Open your browser to `http://localhost:8050`

### Deployment on Render

#### Option 1: Using Render Dashboard (Recommended)

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" and select "Web Service"
4. Connect your GitHub repository
5. Configure the service:
   - **Name**: `renewable-portfolio-dashboard`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:server`
6. Click "Create Web Service"

#### Option 2: Using render.yaml (Infrastructure as Code)

1. Push your code with the included `render.yaml` file to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" and select "Blueprint"
4. Connect your GitHub repository
5. Render will automatically detect and deploy using the `render.yaml` configuration

### Environment Variables

For production deployment, you can set these environment variables:

- `DASH_DEBUG`: Set to `true` for debug mode (default: `false`)
- `PORT`: Port number (default: `8050`)
- `HOST`: Host address (default: `0.0.0.0`)
- `WEB_CONCURRENCY`: Number of worker processes (default: `2`)
- `MAX_DATA_POINTS`: Maximum data points for plots (default: `5000`)
- `CACHE_TIMEOUT`: Cache timeout in seconds (default: `300`)

### Performance Optimizations

The application includes several performance optimizations for production:

- **Caching**: Data loading functions cached for 5-10 minutes
- **Data Sampling**: Large datasets automatically sampled to 5K points max
- **Multiple Workers**: Gunicorn configured with 2 workers by default
- **Memory Management**: Automatic cache cleanup and data reduction
- **Optimized Callbacks**: Reduced unnecessary component updates

### Troubleshooting Performance Issues

If experiencing slow performance on Render:

1. **Check the deployment guide**: See `DEPLOYMENT_FIXES.md` for detailed troubleshooting
2. **Verify Gunicorn command**: Should be `gunicorn app:server --config gunicorn.conf.py`
3. **Monitor response sizes**: Should be <50KB per request
4. **Check resource usage**: CPU <50%, Memory <400MB

For immediate performance issues, add these environment variables:
```
MAX_DATA_POINTS=2000
WEB_CONCURRENCY=1
CACHE_TIMEOUT=600
```

### GHI vs Generation Plots

If the "Generation vs GHI" scatter plots are not working:

1. **Check data columns**: These plots require `generation_mw`, `shortwave_radiation`, and `temperature_2m` columns
2. **Monitor logs**: Enhanced error messages will show exactly what's missing
3. **Increase data points**: Set `MAX_DATA_POINTS=10000` for better scatter plot quality
4. **See debugging guide**: Check `GHI_PLOT_DEBUG.md` for detailed troubleshooting

### Data Structure

The application expects data in the following structure:
```
Renewable Portfolio LLC_parquet/
├── Site_Name_1/
│   ├── Generation/
│   │   ├── forecast/
│   │   │   ├── distribution/
│   │   │   └── timeseries/
│   │   └── historical/
│   ├── Price_da/
│   ├── Price_rt/
│   ├── Revenue_da/
│   └── Revenue_rt/
└── Site_Name_2/
    └── ...
```

## Technology Stack

- **Frontend**: Dash, Plotly, Bootstrap Components
- **Backend**: Python, Pandas, NumPy
- **Data**: Parquet files for optimal performance
- **Deployment**: Gunicorn WSGI server, Render platform

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues or feature requests, please use the in-app suggestion feature or create an issue on GitHub. 