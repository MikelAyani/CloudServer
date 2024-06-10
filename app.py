from flask import Flask, request, jsonify
from vercel_kv_sdk import KV
import pandas as pd
from io import StringIO
import json

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

    # Convert timestamp to datetime and extract week
    df['created'] = pd.to_datetime(df['created'])
    df['week'] = df['created'].dt.isocalendar().week

    # KPI 1: New users created per week
    new_users = df[(df['category'] == 'user') & (df['name'] == 'create')]
    new_users_per_week = new_users.groupby('week')['user_id'].nunique()

    # Detailed information of new users
    new_users_detail = new_users[['week', 'user_id', 'value']].rename(columns={'value': 'organization_id'})

    # Check if new users have entered a workspace within an organization
    for idx, row in new_users_detail.iterrows():
        user_id = row['user_id']
        user_events = df[(df['user_id'] == user_id) & (df['category'] == 'workspace') & (df['name'] == 'enter') & (df['user_id'] != df['value'])]
        if not user_events.empty:
            new_users_detail.at[idx, 'organization_id'] = user_events.iloc[0]['value']

    # Map organization IDs to names
    new_users_detail['organization_name'] = new_users_detail['organization_id'].map(org_map)

    # Calculate the percentage of users that join an organization vs. individual users
    total_new_users = len(new_users_detail)
    users_in_orgs = new_users_detail['organization_id'].notna().sum()
    individual_users = total_new_users - users_in_orgs

    percent_users_in_orgs = (users_in_orgs / total_new_users) * 100
    percent_individual_users = (individual_users / total_new_users) * 100

    print(f"Percentage of users joining organizations: {percent_users_in_orgs:.2f}%")
    print(f"Percentage of individual users: {percent_individual_users:.2f}%")

    # KPI 2: Unique active users per week
    active_users = df[(df['category'] == 'workspace') & (df['name'] == 'enter')]
    active_users_per_week = active_users.groupby('week')['user_id'].nunique()

    # Top 10 active users per week
    top_active_users = active_users.groupby(['week', 'user_id']).size().reset_index(name='counts')
    top_active_users_per_week = top_active_users.sort_values(['week', 'counts'], ascending=[True, False]).groupby('week').head(10)

    # Add organization information for top active users
    top_active_users_per_week['organization_id'] = top_active_users_per_week.apply(
        lambda row: df[(df['user_id'] == row['user_id']) & (df['category'] == 'workspace') & (df['name'] == 'enter') & (df['user_id'] != df['value'])]['value'].values[0] 
        if not df[(df['user_id'] == row['user_id']) & (df['category'] == 'workspace') & (df['name'] == 'enter') & (df['user_id'] != df['value'])].empty else None,
        axis=1
    )
    top_active_users_per_week['organization_name'] = top_active_users_per_week['organization_id'].map(org_map)

    # Calculate average usage rate for individual new users
    individual_new_users = new_users_detail[new_users_detail['organization_id'].isna()]
    individual_usage_events = df[df['user_id'].isin(individual_new_users['user_id']) & (df['category'] == 'workspace') & (df['name'] == 'enter')]
    individual_usage_duration = individual_usage_events.groupby('user_id')['created'].apply(lambda x: x.max() - x.min()).mean()

    print(f"Average usage duration for individual new users: {individual_usage_duration}")

    # KPI 3: Active organizations per week
    active_orgs = active_users[active_users['user_id'] != active_users['value']]
    active_orgs_per_week = active_orgs.groupby('week')['value'].nunique()

    # Top 10 active organizations per week
    top_active_orgs = active_orgs.groupby(['week', 'value']).size().reset_index(name='counts')
    top_active_orgs_per_week = top_active_orgs.sort_values(['week', 'counts'], ascending=[True, False]).groupby('week').head(10)

    # Map organization IDs to names for top active organizations
    top_active_orgs_per_week['organization_name'] = top_active_orgs_per_week['value'].map(org_map)

    # Exclude organizations with expired subscriptions
    current_date = pd.to_datetime('today')
    active_orgs = active_orgs[active_orgs['value'].apply(lambda x: expiration_map.get(x, current_date + pd.DateOffset(days=1)) >= current_date if pd.notna(expiration_map.get(x)) else False)]

    # Organizational health analysis
    org_activity = active_orgs.groupby('value').size()
    healthy_orgs = org_activity[org_activity > org_activity.median()].index.tolist()
    less_active_orgs = org_activity[org_activity <= org_activity.median()].index.tolist()

    healthy_orgs_names = [org_map[org] for org in healthy_orgs if org in org_map]
    less_active_orgs_names = [org_map[org] for org in less_active_orgs if org in org_map]

    if True:
        print("Healthy Organizations:")
        print(healthy_orgs_names)
        print("Less Active Organizations:")
        print(less_active_orgs_names)

        # Display KPIs
        print("New Users Created Per Week:\n", new_users_per_week)
        print("\nDetails of New Users:\n", new_users_detail)
        print("\nUnique Active Users Per Week:\n", active_users_per_week)
        print("\nTop 10 Active Users Per Week:\n", top_active_users_per_week[['week', 'user_id', 'counts', 'organization_name']])
        print("\nActive Organizations Per Week:\n", active_orgs_per_week)
        print("\nTop 10 Active Organizations Per Week:\n", top_active_orgs_per_week[['week', 'organization_name', 'counts']])
        return jsonify({"Result":"Done"})
    
    return jsonify({
        "new_users_per_week": new_users_per_week.to_dict(),
        "percent_users_in_orgs": percent_users_in_orgs,
        "percent_individual_users": percent_individual_users,
        "active_users_per_week": active_users_per_week.to_dict(),
        "top_active_users_per_week": top_active_users_per_week.to_dict(),
        "individual_usage_duration": individual_usage_duration.total_seconds(),
        "active_orgs_per_week": active_orgs_per_week.to_dict(),
        "top_active_orgs_per_week": top_active_orgs_per_week.to_dict(),
        "healthy_orgs_names": healthy_orgs_names,
        "less_active_orgs_names": less_active_orgs_names
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
