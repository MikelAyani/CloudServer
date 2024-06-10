from flask import Flask, request, jsonify
from vercel_kv_sdk import KV
import pandas as pd
from io import StringIO
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024  # 16 MB, adjust as needed

# Initialize Redis connection
redis_client = KV()

@app.route('/api/<key>', methods=['GET'])
def get_data(key):
    data = redis_client.get(key)
    if data:
        return jsonify(json.loads(data))
    else:
        return 'No data found for key: {}'.format(key), 404

@app.route('/api/<key>', methods=['POST'])
def store_data(key):
    if request.is_json:
        data = request.json
    else:
        data = request.data
    if not data or not isinstance(data, dict):
        return 'Invalid JSON data', 400
    redis_client.set(key, json.dumps(data))
    return jsonify({'message': 'Data stored for key: {}'.format(key), 'data': data})

@app.route('/api', methods=['GET'])
def list_data():
    return jsonify({'message': 'Welcome to the API'})

@app.route('/process/test', methods=['POST'])
def process_test():
    # Return processed data in a dictionary
    orgs_csv = request.form['orgs_csv']
    orgs_df = pd.read_csv(StringIO(orgs_csv), delimiter=",")
    return jsonify({"Hello":orgs_df.shape[0]})

@app.route('/process/dashboard', methods=['POST'])
def process_dashboard():
    # Load the events CSV file
    events_csv = request.form['events_csv']
    df = pd.read_csv(StringIO(events_csv), delimiter=";")
    
    # Load the organization CSV file with the correct delimiter
    orgs_csv = request.form['orgs_csv']
    org_df = pd.read_csv(StringIO(orgs_csv), delimiter=",")
 
    # Ensure data is received correctly
    if not events_csv or not orgs_csv:
        return jsonify({"error": "Missing data"}), 400

    # Convert the expiration column to datetime, handling the "Expired" status
    org_df['expiration'] = org_df['expiration'].replace('Expired', pd.NaT)
    org_df['expiration'] = pd.to_datetime(org_df['expiration'], errors='coerce')

    # Create a dictionary to map UUIDs to names and expiration dates
    org_map = pd.Series(org_df.organization_name.values, index=org_df.organization_uuid).to_dict()
    expiration_map = pd.Series(org_df.expiration.values, index=org_df.organization_uuid).to_dict()

    # List of user IDs to exclude from the stats
    exclude_user_ids = [
        'dcc27352-6b00-4cc9-a489-462ab3a12bf3',
        '73fafd55-9745-4e85-b0c8-6214dd8c3bb1',
        '0bdaef3f-dbdc-4d20-b89f-be45ec426831',
        '1871d515-a053-11e8-b24e-000c29a82b4a',
        '19185a41-4497-46c1-9949-e8d1cadc2293'
    ]

    # Exclude specific users from the DataFrame
    df = df[~df['user_id'].isin(exclude_user_ids)]

    # Convert timestamp to datetime and extract week and date
    df['created'] = pd.to_datetime(df['created'])
    df['week'] = df['created'].dt.isocalendar().week
    df['date'] = df['created'].dt.date

    # Define the timeframes
    today = datetime.now()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    last_180_days = today - timedelta(days=180)
    last_25_weeks = today - timedelta(weeks=25)

    # Function to calculate KPIs
    def calculate_kpis(df, org_map, start_date):
        df_timeframe = df[df['created'] >= start_date]
        
        # KPI 1: New users created
        new_users = df_timeframe[(df_timeframe['category'] == 'user') & (df_timeframe['name'] == 'create')]
        new_users_count = new_users['user_id'].nunique()
        
        # Detailed information of new users
        new_users_detail = new_users[['created', 'user_id', 'value']].rename(columns={'value': 'organization_id'})
        
        for idx, row in new_users_detail.iterrows():
            user_id = row['user_id']
            user_events = df[(df['user_id'] == user_id) & (df['category'] == 'workspace') & (df['name'] == 'enter') & (df['user_id'] != df['value'])]
            if not user_events.empty:
                new_users_detail.at[idx, 'organization_id'] = user_events.iloc[0]['value']
        
        new_users_detail['organization_name'] = new_users_detail['organization_id'].map(org_map)
        
        total_new_users = len(new_users_detail)
        users_in_orgs = new_users_detail['organization_id'].notna().sum()
        individual_users = total_new_users - users_in_orgs
        
        percent_users_in_orgs = (users_in_orgs / total_new_users) * 100 if total_new_users > 0 else 0
        percent_individual_users = (individual_users / total_new_users) * 100 if total_new_users > 0 else 0
        
        # KPI 2: Unique active users
        active_users = df_timeframe[(df_timeframe['category'] == 'workspace') & (df_timeframe['name'] == 'enter')]
        active_users_count = active_users['user_id'].nunique()
        
        # KPI 3: Active organizations
        active_orgs = active_users[active_users['user_id'] != active_users['value']]
        active_orgs_count = active_orgs['value'].nunique()
        
        # Top 10 active organizations
        top_active_orgs = active_orgs.groupby('value').size().reset_index(name='counts')
        top_active_orgs = top_active_orgs.sort_values(by='counts', ascending=False).head(10)
        top_active_orgs['organization_name'] = top_active_orgs['value'].map(org_map)
        
        top_active_orgs_list = top_active_orgs[['organization_name', 'counts']].to_dict(orient='records')
        
        # Identify critical organizations
        critical_org_threshold = 5  # Define your own threshold
        critical_orgs = active_orgs.groupby('value').size()
        critical_orgs = critical_orgs[critical_orgs < critical_org_threshold].reset_index(name='counts')
        critical_orgs['organization_name'] = critical_orgs['value'].map(org_map)
        critical_orgs_list = critical_orgs[['organization_name', 'counts']].to_dict(orient='records')
        
        return {
            'new_users_count': new_users_count,
            'percent_users_in_orgs': percent_users_in_orgs,
            'percent_individual_users': percent_individual_users,
            'active_users_count': active_users_count,
            'active_orgs_count': active_orgs_count,
            'top_active_orgs': top_active_orgs_list,
            'critical_orgs': critical_orgs_list
        }

    # Calculate KPIs for last 7 days, last 30 days, and last 180 days
    kpis_last_7_days = calculate_kpis(df, org_map, last_7_days)
    kpis_last_30_days = calculate_kpis(df, org_map, last_30_days)
    kpis_last_180_days = calculate_kpis(df, org_map, last_180_days)

    # Calculate weekly analysis for the last 25 weeks
    def weekly_analysis(df, start_date):
        df_timeframe = df[df['created'] >= start_date]
        df_timeframe['week_start'] = df_timeframe['created'].dt.to_period('W').apply(lambda r: r.start_time)
        
        weekly_new_users = df_timeframe[(df_timeframe['category'] == 'user') & (df_timeframe['name'] == 'create')].groupby('week_start')['user_id'].nunique().reset_index(name='new_users_count')
        weekly_active_users = df_timeframe[(df_timeframe['category'] == 'workspace') & (df_timeframe['name'] == 'enter')].groupby('week_start')['user_id'].nunique().reset_index(name='active_users_count')
        weekly_active_orgs = df_timeframe[(df_timeframe['category'] == 'workspace') & (df_timeframe['name'] == 'enter') & (df_timeframe['user_id'] != df_timeframe['value'])].groupby('week_start')['value'].nunique().reset_index(name='active_orgs_count')
        
        weekly_data = pd.merge(weekly_new_users, weekly_active_users, on='week_start', how='outer')
        weekly_data = pd.merge(weekly_data, weekly_active_orgs, on='week_start', how='outer').fillna(0)
        
        return {
            'weeks': weekly_data['week_start'].dt.strftime('%Y-%m-%d').tolist(),
            'new_users_count': weekly_data['new_users_count'].astype(int).tolist(),
            'active_users_count': weekly_data['active_users_count'].astype(int).tolist(),
            'active_orgs_count': weekly_data['active_orgs_count'].astype(int).tolist()
        }

    weekly_kpis = weekly_analysis(df, last_25_weeks)

    # Aggregate all KPIs into a single dictionary
    kpis = {
        "last_7_days": kpis_last_7_days,
        "last_30_days": kpis_last_30_days,
        "last_180_days": kpis_last_180_days,
        "weekly_analysis": weekly_kpis
    }

    return jsonify(kpis)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
