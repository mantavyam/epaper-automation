#!/usr/bin/env python3
"""
Maintenance utilities for the e-newspaper automation system
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import argparse


def view_history(days=7):
    """View recent download history"""
    if not os.path.exists('download_history.json'):
        print("❌ No history file found")
        return
    
    with open('download_history.json', 'r') as f:
        history = json.load(f)
    
    dates = sorted(history.keys(), reverse=True)[:days]
    
    print(f"\n📊 Download History (Last {days} days)\n")
    print("=" * 70)
    
    for date in dates:
        print(f"\n📅 {date}")
        newspapers = history[date]
        
        for newspaper, data in newspapers.items():
            status = "✅" if "file_path" in data else "⚠️"
            print(f"  {status} {newspaper}")
            
            if "file_path" in data:
                file_path = Path(data["file_path"])
                if file_path.exists():
                    size = file_path.stat().st_size / (1024 * 1024)
                    print(f"      📁 {file_path} ({size:.2f} MB)")
                else:
                    print(f"      ⚠️  File not found: {file_path}")
            
            if "pdf_url" in data:
                print(f"      🔗 {data['pdf_url']}")
            
            if "fallback_url" in data:
                print(f"      🔗 Fallback: {data['fallback_url']}")


def check_storage():
    """Check storage usage"""
    if not os.path.exists('e-paper'):
        print("❌ No e-paper folder found")
        return
    
    print("\n💾 Storage Analysis\n")
    print("=" * 70)
    
    total_size = 0
    folder_stats = {}
    
    for root, dirs, files in os.walk('e-paper'):
        for file in files:
            if file.endswith('.pdf'):
                file_path = Path(root) / file
                size = file_path.stat().st_size
                total_size += size
                
                # Get month folder
                month_folder = Path(root).name
                folder_stats[month_folder] = folder_stats.get(month_folder, 0) + size
    
    # Display by folder
    for folder, size in sorted(folder_stats.items()):
        size_mb = size / (1024 * 1024)
        print(f"📁 {folder:<10} {size_mb:>8.2f} MB")
    
    print("-" * 70)
    total_mb = total_size / (1024 * 1024)
    total_gb = total_size / (1024 * 1024 * 1024)
    print(f"📊 Total:      {total_mb:>8.2f} MB ({total_gb:.3f} GB)")
    
    # GitHub storage limits
    limit_mb = 500 if os.path.exists('.git/config') else 1024
    usage_percent = (total_mb / limit_mb) * 100
    
    print(f"\n🎯 GitHub Limit: {limit_mb} MB")
    print(f"📈 Usage: {usage_percent:.1f}%")
    
    if usage_percent > 80:
        print("⚠️  Warning: Approaching storage limit!")
    elif usage_percent > 50:
        print("💡 Tip: Consider enabling Git LFS")


def cleanup_old_files(days=30):
    """Manually cleanup files older than X days"""
    if not os.path.exists('e-paper'):
        print("❌ No e-paper folder found")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    deleted_size = 0
    
    print(f"\n🧹 Cleaning files older than {days} days ({cutoff_date.date()})\n")
    
    for root, dirs, files in os.walk('e-paper'):
        for file in files:
            if file.endswith('.pdf'):
                file_path = Path(root) / file
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if mtime < cutoff_date:
                    size = file_path.stat().st_size
                    print(f"🗑️  Deleting: {file_path} ({mtime.date()})")
                    file_path.unlink()
                    deleted_count += 1
                    deleted_size += size
    
    if deleted_count > 0:
        print(f"\n✅ Deleted {deleted_count} files ({deleted_size / (1024*1024):.2f} MB)")
    else:
        print("✅ No old files to delete")
    
    # Remove empty directories
    for root, dirs, files in os.walk('e-paper', topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            if not any(dir_path.iterdir()):
                print(f"🗑️  Removing empty folder: {dir_path}")
                dir_path.rmdir()


def verify_setup():
    """Verify the automation setup"""
    print("\n🔍 Verifying Setup\n")
    print("=" * 70)
    
    checks = {
        "scraper.py exists": os.path.exists('scraper.py'),
        "requirements.txt exists": os.path.exists('requirements.txt'),
        "GitHub workflow exists": os.path.exists('.github/workflows/daily-newspaper.yml'),
        ".env.example exists": os.path.exists('.env.example'),
        ".env configured": os.path.exists('.env'),
        "DISCORD_WEBHOOK_URL set": bool(os.getenv('DISCORD_WEBHOOK_URL')),
        "e-paper folder exists": os.path.exists('e-paper'),
        "download_history.json exists": os.path.exists('download_history.json'),
    }
    
    for check, status in checks.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {check}")
    
    all_passed = all(checks.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All checks passed! System is ready.")
    else:
        print("⚠️  Some checks failed. Please review above.")
    
    return all_passed


def export_links():
    """Export all PDF links to a text file"""
    if not os.path.exists('download_history.json'):
        print("❌ No history file found")
        return
    
    with open('download_history.json', 'r') as f:
        history = json.load(f)
    
    output_file = f"newspaper_links_{datetime.now().strftime('%Y%m%d')}.txt"
    
    with open(output_file, 'w') as f:
        f.write("E-Newspaper PDF Links\n")
        f.write("=" * 70 + "\n\n")
        
        for date in sorted(history.keys(), reverse=True):
            f.write(f"\n{date}\n")
            f.write("-" * 40 + "\n")
            
            newspapers = history[date]
            for newspaper, data in newspapers.items():
                f.write(f"{newspaper}:\n")
                
                if "pdf_url" in data:
                    f.write(f"  {data['pdf_url']}\n")
                elif "fallback_url" in data:
                    f.write(f"  {data['fallback_url']}\n")
                
                f.write("\n")
    
    print(f"✅ Links exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Maintenance utilities for e-newspaper automation"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # History command
    history_parser = subparsers.add_parser('history', help='View download history')
    history_parser.add_argument('--days', type=int, default=7, help='Number of days to show')
    
    # Storage command
    subparsers.add_parser('storage', help='Check storage usage')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old files')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete files older than X days')
    
    # Verify command
    subparsers.add_parser('verify', help='Verify setup')
    
    # Export command
    subparsers.add_parser('export', help='Export PDF links to text file')
    
    args = parser.parse_args()
    
    if args.command == 'history':
        view_history(args.days)
    elif args.command == 'storage':
        check_storage()
    elif args.command == 'cleanup':
        cleanup_old_files(args.days)
    elif args.command == 'verify':
        verify_setup()
    elif args.command == 'export':
        export_links()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
