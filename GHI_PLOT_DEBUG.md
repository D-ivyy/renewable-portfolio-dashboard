# 🔍 GHI vs Generation Plots - Debugging Guide

## 🚨 Issue Description
The "Generation vs GHI" plots (both hourly and temperature versions) are not working after the performance optimizations were applied.

## ✅ Fixes Applied

### 1. **Restored Data Coverage**
- **GHI Hour Plot**: Restored from 5 years back to 10 years of data
- **GHI Temp Plot**: Restored from 3 years back to 5 years of data
- **Data Sampling**: Increased limits for scatter plots (10K+ points for better visualization)

### 2. **Improved Data Filtering**
- **Generation threshold**: Reduced from 0.1 MW to 0.01 MW (more inclusive)
- **Dynamic sampling**: Now uses `MAX_DATA_POINTS` environment variable
- **Smart limits**: 2x points for hour plot, 1.5x for temp plot

### 3. **Better Error Handling**
- ✅ **Column validation**: Checks for required columns before processing
- ✅ **Debug output**: Prints missing columns and available columns to logs
- ✅ **Graceful degradation**: Shows specific error messages instead of crashing

## 🔧 Required Data Columns

### For GHI Hour Plot:
```
- generation_mw
- shortwave_radiation  
- hour
- year
- datetime (or year/month/day/hour)
```

### For GHI Temperature Plot:
```
- generation_mw
- shortwave_radiation
- temperature_2m
- hour  
- year
- datetime (or year/month/day/hour)
```

## 🐛 Debugging Steps

### Step 1: Check Render Logs
After redeployment, check for these messages:
```
❌ Missing columns for GHI hour plot: [column_names]
📋 Available columns: [actual_columns]
```

### Step 2: Verify Data Structure
Your historical files should be located at:
```
Renewable Portfolio LLC_parquet/
├── Site_Name/
│   └── Generation/
│       └── historical/
│           └── Site_Name_generation_hourly_historical.parquet
```

### Step 3: Test Locally First
Run locally to see exact error messages:
```bash
python app.py
# Navigate to Generation → GHI vs Generation plots
# Check console output for missing columns
```

## 🎯 Environment Variables for Tuning

Add these to Render environment variables if needed:

### For More Data Points:
```
MAX_DATA_POINTS=10000  # Default is 5000
```

### For Emergency Performance:
```
MAX_DATA_POINTS=2000   # Reduce if still slow
```

## 🔍 Common Issues & Solutions

### Issue 1: "Missing required data columns"
**Cause**: Historical parquet files don't have weather data columns
**Solution**: 
1. Check if your data includes `shortwave_radiation` and `temperature_2m`
2. If missing, you may need to regenerate historical files with weather data
3. Or hide these plot types if weather data unavailable

### Issue 2: "No complete years of data available"  
**Cause**: Not enough hourly data (need 8760+ hours per year)
**Solution**:
1. Check data completeness in your historical files
2. Reduce minimum year requirements in code if needed

### Issue 3: "Insufficient data for analysis"
**Cause**: Too few data points after filtering
**Solution**:
1. Increase `MAX_DATA_POINTS` environment variable
2. Check if filtering conditions are too strict

### Issue 4: Plots load but show empty/weird patterns
**Cause**: Data sampling too aggressive or wrong units
**Solution**:
1. Increase `MAX_DATA_POINTS` to 10000+
2. Check data units (MW vs kW, W/m² vs other)

## 📊 Expected Data Ranges

### Generation:
- **Range**: 0.01 - [Site Capacity] MW
- **Pattern**: Should correlate with GHI

### GHI (shortwave_radiation):
- **Range**: 0 - 1200 W/m²
- **Peak**: Around 1000-1200 W/m² at solar noon

### Temperature:
- **Range**: Varies by location (-10°C to 50°C typical)
- **Pattern**: Should show performance impact at extreme temps

## 🚀 Deployment Steps

1. **Push fixes to GitHub:**
   ```bash
   git add .
   git commit -m "Fix GHI plots with better data coverage and error handling"
   git push origin main
   ```

2. **Monitor Render logs** for the debug messages

3. **Test plots** and check for specific error messages

4. **Adjust environment variables** if needed based on logs

## 🔗 Related Files Modified
- `app.py`: Enhanced GHI plot functions with better error handling
- Environment variables: Can tune `MAX_DATA_POINTS` for performance vs quality

---

**If plots still don't work after this:** Check the Render logs for the specific error messages. The enhanced error handling will tell you exactly what's missing! 