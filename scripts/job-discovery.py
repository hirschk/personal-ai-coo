#!/usr/bin/env python3
"""
Job Discovery Engine for Sterl OS
Runs daily (Mon/Wed/Fri 11am EST via cron)
1. Scrapes LinkedIn jobs via Apify API
2. Scores against candidate profile + network
3. Outputs top 5 to Google Sheet + Telegram
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from collections import defaultdict
import difflib

# Configuration
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN")
APIFY_ACTOR = "openclaw/linkedin-jobs-scraper"
WORKSPACE = "/root/.openclaw/workspace"

# Target parameters
TARGET_ROLES = {
    "head of product": 1.0,
    "vp product": 0.95,
    "director of product": 0.90,
    "senior product manager": 0.70,
    "product manager": 0.40,
}

TARGET_INDUSTRIES = {
    "fintech": 1.0,
    "ai": 1.0,
    "ai-native": 1.0,
    "payments": 0.9,
    "commerce": 0.8,
    "saas": 0.7,
}

def load_network():
    """Load network.md and build company→contacts index"""
    network_file = os.path.join(WORKSPACE, "network.md")
    companies = defaultdict(list)
    
    try:
        with open(network_file, 'r') as f:
            content = f.read()
            in_table = False
            for line in content.split('\n'):
                if line.startswith('|') and 'Name' in line:
                    in_table = True
                    continue
                if in_table and line.startswith('|'):
                    parts = [p.strip() for p in line.split('|')[1:-1]]
                    if len(parts) >= 3:
                        name, company, title = parts[0], parts[1], parts[2]
                        if name and company and title:
                            companies[company.lower()].append({
                                'name': name,
                                'title': title,
                                'company': company
                            })
    except Exception as e:
        print(f"Error loading network: {e}", file=sys.stderr)
    
    return companies

def fuzzy_match_company(job_company, network_companies, threshold=0.8):
    """Fuzzy match job company against network companies"""
    job_lower = job_company.lower().strip()
    
    for net_company in network_companies.keys():
        ratio = difflib.SequenceMatcher(None, job_lower, net_company).ratio()
        if ratio >= threshold:
            return net_company, network_companies[net_company]
    
    return None, []

def calculate_fit_score(job_title, job_description):
    """Calculate fit score based on title and description"""
    title_lower = job_title.lower()
    desc_lower = job_description.lower() if job_description else ""
    
    # Role match
    role_score = 0.0
    for role, weight in TARGET_ROLES.items():
        if role in title_lower:
            role_score = max(role_score, weight)
    
    # Industry match
    industry_score = 0.0
    for industry, weight in TARGET_INDUSTRIES.items():
        if industry in desc_lower or industry in title_lower:
            industry_score = max(industry_score, weight)
    
    # Seniority (assume 10 YOE, looking for 5-12 YOE roles)
    seniority_score = 0.9
    if "junior" in title_lower or "entry" in desc_lower:
        seniority_score = 0.4
    elif "principal" in title_lower or "distinguished" in desc_lower:
        seniority_score = 0.7
    
    fit_score = (0.5 * role_score) + (0.3 * industry_score) + (0.2 * seniority_score)
    return min(fit_score, 1.0)

def calculate_recency_score(posted_at):
    """Calculate recency score"""
    try:
        # Try parsing ISO format
        if 'T' in posted_at:
            post_date = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
        else:
            # Assume YYYY-MM-DD format
            post_date = datetime.strptime(posted_at, '%Y-%m-%d')
        
        days_old = (datetime.now() - post_date.replace(tzinfo=None) if post_date.tzinfo else post_date).days
        
        if days_old < 2:
            return 1.0
        elif days_old < 4:
            return 0.8
        elif days_old < 7:
            return 0.5
        elif days_old < 14:
            return 0.2
        else:
            return 0.0
    except:
        return 0.5

def score_jobs(jobs, network_companies):
    """Score all jobs and return ranked list"""
    scored = []
    
    for job in jobs:
        fit_score = calculate_fit_score(job.get('title', ''), job.get('descriptionText', ''))
        recency_score = calculate_recency_score(job.get('postedAt', ''))
        
        # Network score
        network_score = 0.0
        network_path = None
        matched_company, contacts = fuzzy_match_company(job.get('companyName', ''), network_companies)
        
        if contacts:
            # Check if any contact is in product/PM role
            for contact in contacts:
                if any(x in contact['title'].lower() for x in ['product', 'pm', 'chief product']):
                    network_score = 1.0
                    network_path = f"{contact['name']} (PM at {matched_company})"
                    break
            
            # Check if any contact is in recruiting/talent
            if network_score == 0.0:
                for contact in contacts:
                    if any(x in contact['title'].lower() for x in ['recruiter', 'talent', 'hiring']):
                        network_score = 0.8
                        network_path = f"{contact['name']} (Recruiter at {matched_company})"
                        break
            
            # Any contact at company
            if network_score == 0.0 and contacts:
                network_score = 0.6
                network_path = f"{contacts[0]['name']} ({matched_company})"
        
        priority_score = (0.4 * fit_score) + (0.4 * network_score) + (0.2 * recency_score)
        
        scored.append({
            'job_id': job.get('id', ''),
            'title': job.get('title', ''),
            'company': job.get('companyName', ''),
            'url': job.get('link', ''),
            'posted_at': job.get('postedAt', ''),
            'fit_score': round(fit_score, 2),
            'network_score': round(network_score, 2),
            'recency_score': round(recency_score, 2),
            'priority_score': round(priority_score, 2),
            'network_path': network_path,
            'description': job.get('descriptionText', '')[:500],
        })
    
    return sorted(scored, key=lambda x: x['priority_score'], reverse=True)

def call_apify_api(run_input):
    """Call Apify API to scrape LinkedIn jobs"""
    try:
        url = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/runs?token={APIFY_API_TOKEN}"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        data = json.dumps(run_input).encode('utf-8')
        
        print(f"Calling Apify API: {APIFY_ACTOR}...")
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            run_id = result['data']['id']
            print(f"  Started run: {run_id}")
            
            # Poll for completion (max 2 min)
            import time
            start = time.time()
            while time.time() - start < 120:
                status_url = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/runs/{run_id}?token={APIFY_API_TOKEN}"
                status_req = urllib.request.Request(status_url)
                
                with urllib.request.urlopen(status_req, timeout=10) as status_response:
                    status = json.loads(status_response.read().decode())
                    if status['data']['status'] in ['SUCCEEDED', 'FAILED']:
                        print(f"  Run {status['data']['status']}")
                        
                        # Fetch results
                        if status['data']['status'] == 'SUCCEEDED':
                            dataset_id = status['data']['defaultDatasetId']
                            items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}"
                            items_req = urllib.request.Request(items_url)
                            
                            with urllib.request.urlopen(items_req, timeout=10) as items_response:
                                items = json.loads(items_response.read().decode())
                                return items if isinstance(items, list) else []
                        return []
                
                time.sleep(5)
            
            print("  Run timeout")
            return []
    
    except Exception as e:
        print(f"  Error calling Apify: {e}", file=sys.stderr)
        return []

def main():
    print(f"[{datetime.now().isoformat()}] Starting job discovery...")
    
    # Step 1: Load network
    print("Loading network...")
    network_companies = load_network()
    print(f"  Loaded {len(network_companies)} companies")
    
    # Step 2: Call Apify scraper
    print("Calling Apify LinkedIn Jobs Scraper...")
    apify_input = {
        "startUrls": [
            {"url": "https://www.linkedin.com/jobs/search/?keywords=Head%20of%20Product&location=United%20States"},
            {"url": "https://www.linkedin.com/jobs/search/?keywords=VP%20Product&location=United%20States"},
        ],
        "maxItems": 50,
        "scrapeCompany": True,
        "scrapeJobDetails": True,
    }
    
    jobs = call_apify_api(apify_input)
    print(f"  Scraped {len(jobs)} jobs")
    
    if not jobs:
        print("  No jobs scraped. Check API token and actor ID.")
        return 1
    
    # Step 3: Score jobs
    print("Scoring jobs...")
    scored_jobs = score_jobs(jobs, network_companies)
    print(f"  Scored {len(scored_jobs)} jobs")
    
    # Step 4: Output top 5
    top_5 = scored_jobs[:5]
    print("\nTop 5 Opportunities:")
    for i, job in enumerate(top_5, 1):
        print(f"{i}. {job['title']} @ {job['company']} (Score: {job['priority_score']})")
        if job['network_path']:
            print(f"   Network: {job['network_path']}")
    
    # Step 5: Save to file
    output_file = os.path.join(WORKSPACE, 'jobs-today.json')
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_scraped': len(jobs),
            'top_5': top_5,
            'all_scored': scored_jobs[:20],
        }, f, indent=2)
    print(f"\nSaved to {output_file}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
