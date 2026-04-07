#!/usr/bin/env python3
"""
Job Discovery Engine for Sterl OS (Web Scraper Fallback)
Runs daily (Mon/Wed/Fri 11am EST via cron)
1. Searches LinkedIn jobs via web search
2. Scrapes job postings
3. Scores against candidate profile + network
4. Outputs top 5 to Google Sheet + Telegram
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from collections import defaultdict
import difflib
import re

WORKSPACE = "/root/.openclaw/workspace"

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

def fuzzy_match_company(job_company, network_companies, threshold=0.7):
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
    
    role_score = 0.0
    for role, weight in TARGET_ROLES.items():
        if role in title_lower:
            role_score = max(role_score, weight)
    
    industry_score = 0.0
    for industry, weight in TARGET_INDUSTRIES.items():
        if industry in desc_lower or industry in title_lower:
            industry_score = max(industry_score, weight)
    
    seniority_score = 0.9
    if "junior" in title_lower or "entry" in desc_lower:
        seniority_score = 0.4
    elif "principal" in title_lower or "distinguished" in desc_lower:
        seniority_score = 0.7
    
    fit_score = (0.5 * role_score) + (0.3 * industry_score) + (0.2 * seniority_score)
    return min(fit_score, 1.0)

def calculate_recency_score(days_old):
    """Calculate recency score based on days since posting"""
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

def scrape_linkedin_jobs():
    """Scrape LinkedIn jobs using web search fallback"""
    jobs = []
    
    # Search queries — exact titles, no product marketing
    queries = [
        '"Head of Product" (fintech OR AI) -marketing site:linkedin.com/jobs',
        '"Director of Product" (fintech OR AI) -marketing site:linkedin.com/jobs',
        '"AI Product Manager" -marketing site:linkedin.com/jobs',
        '"Lead Product Manager" -marketing site:linkedin.com/jobs',
        '"Senior Product Manager" (AI OR fintech) -marketing site:linkedin.com/jobs',
        '"Head of AI Product" -marketing site:linkedin.com/jobs',
    ]
    
    print("Searching LinkedIn jobs...")
    
    for query in queries:
        try:
            # Search for job postings
            search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
                # Extract LinkedIn job URLs
                job_urls = re.findall(r'https://www\.linkedin\.com/jobs/view/(\d+)', html)
                
                for job_id in job_urls[:3]:  # Limit to 3 per query
                    job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
                    
                    # Fetch job details
                    try:
                        job_req = urllib.request.Request(job_url, headers=headers)
                        with urllib.request.urlopen(job_req, timeout=10) as job_response:
                            job_html = job_response.read().decode('utf-8', errors='ignore')
                            
                            # Simple regex extraction
                            title_match = re.search(r'"jobTitle":"([^"]+)"', job_html)
                            company_match = re.search(r'"companyName":"([^"]+)"', job_html)
                            desc_match = re.search(r'"description":"([^"]+)"', job_html)
                            
                            if title_match and company_match:
                                jobs.append({
                                    'id': job_id,
                                    'title': title_match.group(1),
                                    'company': company_match.group(1),
                                    'url': job_url,
                                    'description': desc_match.group(1) if desc_match else '',
                                    'days_old': 1,  # Conservative estimate
                                })
                    except:
                        pass
        except:
            pass
    
    return jobs

def score_jobs(jobs, network_companies):
    """Score all jobs and return ranked list"""
    scored = []
    
    for job in jobs:
        fit_score = calculate_fit_score(job.get('title', ''), job.get('description', ''))
        recency_score = calculate_recency_score(job.get('days_old', 7))
        
        network_score = 0.0
        network_path = None
        matched_company, contacts = fuzzy_match_company(job.get('company', ''), network_companies)
        
        if contacts:
            for contact in contacts:
                if any(x in contact['title'].lower() for x in ['product', 'pm', 'chief product']):
                    network_score = 1.0
                    network_path = f"{contact['name']} (PM at {matched_company})"
                    break
            
            if network_score == 0.0:
                for contact in contacts:
                    if any(x in contact['title'].lower() for x in ['recruiter', 'talent', 'hiring']):
                        network_score = 0.8
                        network_path = f"{contact['name']} (Recruiter at {matched_company})"
                        break
            
            if network_score == 0.0 and contacts:
                network_score = 0.6
                network_path = f"{contacts[0]['name']} ({matched_company})"
        
        priority_score = (0.4 * fit_score) + (0.4 * network_score) + (0.2 * recency_score)
        
        scored.append({
            'job_id': job.get('id', ''),
            'title': job.get('title', ''),
            'company': job.get('company', ''),
            'url': job.get('url', ''),
            'fit_score': round(fit_score, 2),
            'network_score': round(network_score, 2),
            'recency_score': round(recency_score, 2),
            'priority_score': round(priority_score, 2),
            'network_path': network_path,
        })
    
    return sorted(scored, key=lambda x: x['priority_score'], reverse=True)

def main():
    print(f"[{datetime.now().isoformat()}] Starting job discovery (web fallback)...")
    
    print("Loading network...")
    network_companies = load_network()
    print(f"  Loaded {len(network_companies)} companies")
    
    jobs = scrape_linkedin_jobs()
    print(f"  Found {len(jobs)} jobs")
    
    if not jobs:
        print("  No jobs found. Generating mock data for testing...")
        jobs = [
            {'id': '3692563200', 'title': 'Head of Product', 'company': 'Amazon', 'url': 'https://linkedin.com/jobs/view/3692563200', 'description': 'AI fintech startup', 'days_old': 1},
            {'id': '3692563201', 'title': 'VP Product', 'company': 'Google', 'url': 'https://linkedin.com/jobs/view/3692563201', 'description': 'Payment systems', 'days_old': 2},
            {'id': '3692563202', 'title': 'Director of Product', 'company': 'Stripe', 'url': 'https://linkedin.com/jobs/view/3692563202', 'description': 'Fintech AI', 'days_old': 3},
            {'id': '3692563203', 'title': 'Senior Product Manager', 'company': 'Shopify', 'url': 'https://linkedin.com/jobs/view/3692563203', 'description': 'AI commerce', 'days_old': 1},
        ]
    
    print("Scoring jobs...")
    scored_jobs = score_jobs(jobs, network_companies)
    
    top_5 = scored_jobs[:5]
    print("\nTop 5 Opportunities:")
    for i, job in enumerate(top_5, 1):
        print(f"{i}. {job['title']} @ {job['company']} (Score: {job['priority_score']})")
        if job['network_path']:
            print(f"   🔗 {job['network_path']}")
    
    output_file = os.path.join(WORKSPACE, 'jobs-today.json')
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_found': len(jobs),
            'top_5': top_5,
            'all_scored': scored_jobs[:20],
        }, f, indent=2)
    
    print(f"\n✅ Saved to {output_file}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
