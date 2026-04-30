#!/usr/bin/env python3
"""Quick scrape + score + sheet update"""

import json
import os
import urllib.request
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
import time
from datetime import datetime
from collections import defaultdict
import difflib

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN")
ACTOR = "openclaw~linkedin-jobs-scraper"
WORKSPACE = "/root/.openclaw/workspace"
SHEET_ID = "1hbT8236Mh9_H4Ri6lTlwuCNvT1jdXTIBR91A3roNFXs"

TARGET_ROLES = {
    "head of product": 1.0,
    "director of product": 0.95,
    "ai product manager": 0.90,
    "lead product manager": 0.85,
    "senior product manager": 0.80,
}

def load_network():
    """Load network"""
    companies = defaultdict(list)
    try:
        with open(f"{WORKSPACE}/network.md") as f:
            in_table = False
            for line in f:
                if 'Name' in line and '|' in line:
                    in_table = True
                    continue
                if in_table and line.startswith('|'):
                    parts = [p.strip() for p in line.split('|')[1:-1]]
                    if len(parts) >= 3:
                        name, company, title = parts[0], parts[1], parts[2]
                        if name and company:
                            companies[company.lower()].append({'name': name, 'title': title})
    except:
        pass
    return companies

def fuzzy_match(job_company, network, threshold=0.65):
    """Match company"""
    job_lower = job_company.lower().strip()
    for net_comp in network.keys():
        if difflib.SequenceMatcher(None, job_lower, net_comp).ratio() >= threshold:
            return net_comp, network[net_comp]
    return None, []

def score_job(job, network):
    """Score a job"""
    title_lower = job.get('title', '').lower()
    location = job.get('location', '').lower()
    
    # Fit score
    role_score = 0.0
    for role, weight in TARGET_ROLES.items():
        if role in title_lower:
            role_score = max(role_score, weight)
    
    # Location score (check if in target cities or remote)
    location_score = 1.0 if any(x in location for x in ['austin', 'miami', 'los angeles', 'new york', 'san francisco', 'remote', 'hybrid']) else 0.3
    
    fit_score = (0.6 * role_score) + (0.4 * location_score)
    
    # Network score
    network_score = 0.0
    network_path = None
    matched_comp, contacts = fuzzy_match(job.get('companyName', ''), network)
    
    if contacts:
        for contact in contacts:
            if any(x in contact['title'].lower() for x in ['product', 'pm']):
                network_score = 1.0
                network_path = f"{contact['name']} (PM)"
                break
        
        if not network_path and contacts:
            network_score = 0.5
            network_path = f"{contacts[0]['name']}"
    
    priority = (0.4 * fit_score) + (0.6 * network_score)
    
    return {
        'title': job.get('title', ''),
        'company': job.get('companyName', ''),
        'location': job.get('location', ''),
        'url': job.get('link', ''),
        'posted': job.get('postedAt', ''),
        'fit_score': round(fit_score, 2),
        'network_score': round(network_score, 2),
        'priority_score': round(priority, 2),
        'network_path': network_path or 'No connection',
    }

def call_apify(urls):
    """Call Apify"""
    url = f"https://api.apify.com/v2/acts/{ACTOR}/runs?token={APIFY_TOKEN}"
    payload = {
        "startUrls": [{"url": u} for u in urls],
        "maxItems": 50,
        "scrapeCompany": True,
        "scrapeJobDetails": True,
    }
    
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode())
        run_id = result['data']['id']
        print(f"Run: {run_id}")
    
    # Poll
    start = time.time()
    while time.time() - start < 180:
        status_url = f"https://api.apify.com/v2/acts/{ACTOR}/runs/{run_id}?token={APIFY_TOKEN}"
        status_req = urllib.request.Request(status_url)
        
        with urllib.request.urlopen(status_req, timeout=10) as status_response:
            status = json.loads(status_response.read().decode())
            if status['data']['status'] == 'SUCCEEDED':
                dataset_id = status['data']['defaultDatasetId']
                items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
                items_req = urllib.request.Request(items_url)
                
                with urllib.request.urlopen(items_req, timeout=10) as items_response:
                    return json.loads(items_response.read().decode())
            elif status['data']['status'] in ['FAILED', 'TIMED-OUT']:
                return []
        
        time.sleep(4)
    
    return []

def update_sheet(jobs):
    """Update Google Sheet"""
    import subprocess
    
    rows = []
    for job in jobs[:5]:
        rows.append([
            job['company'],
            job['title'],
            job['location'],
            f"{job['priority_score']:.2f}",
            job['network_path'],
        ])
    
    try:
        subprocess.run([
            'bash', '-c',
            f'''GOG_KEYRING_PASSWORD=sterl-gog-keyring gog sheets update {SHEET_ID} "Sheet1!A2:E6" --values-json '{json.dumps(rows)}' --input USER_ENTERED'''
        ], timeout=10, capture_output=True)
        print("✅ Sheet updated")
    except Exception as e:
        print(f"Sheet update failed: {e}")

def main():
    print(f"[{datetime.now().isoformat()}] Scrape + Score\n")
    
    print("Loading network...")
    network = load_network()
    print(f"  {len(network)} companies\n")
    
    print("Calling Apify...")
    urls = [
        "https://www.linkedin.com/jobs/search/?keywords=Head%20of%20Product&location=United%20States",
        "https://www.linkedin.com/jobs/search/?keywords=Director%20of%20Product&location=United%20States",
        "https://www.linkedin.com/jobs/search/?keywords=AI%20Product%20Manager&location=United%20States",
    ]
    
    jobs = call_apify(urls)
    print(f"  {len(jobs)} jobs scraped\n")
    
    if not jobs:
        print("No jobs found")
        return 1
    
    print("Scoring...")
    scored = [score_job(j, network) for j in jobs]
    scored.sort(key=lambda x: x['priority_score'], reverse=True)
    
    print(f"\n🎯 Top 5:\n")
    for i, job in enumerate(scored[:5], 1):
        print(f"{i}. {job['title']} @ {job['company']}")
        print(f"   Score: {job['priority_score']} | 🔗 {job['network_path']}")
        print(f"   {job['location']} | Posted: {job['posted']}\n")
    
    # Save
    with open(f"{WORKSPACE}/jobs-today.json", 'w') as f:
        json.dump({'timestamp': datetime.now().isoformat(), 'top_5': scored[:5]}, f, indent=2)
    
    # Update sheet
    update_sheet(scored)
    
    print("Done ✅")
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())

EOF
