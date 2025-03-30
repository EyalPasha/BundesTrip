import os
import csv
from datetime import datetime, timedelta

def fix_dates(file_path):
    """Add appropriate years to dates in the games file"""
    # Get today's date
    today = datetime.now()
    current_year = today.year
    next_year = current_year + 1
    
    # Create a temp file for writing
    temp_file = file_path + ".temp"
    
    # Read header and data from original file
    with open(file_path, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
    
    # Process the file
    updated_lines = []
    header_processed = False
    
    for line in lines:
        if not header_processed and line.strip().startswith('League'):
            # Keep the header as is
            updated_lines.append(line)
            header_processed = True
            continue
            
        if ',' not in line:
            # Keep non-data lines as is
            updated_lines.append(line)
            continue
        
        # Split the line but preserve the original structure
        parts = line.split(',', 3)
        if len(parts) < 3:
            # Not enough parts, keep as is
            updated_lines.append(line)
            continue
        
        league = parts[0].strip()
        date_str = parts[1].strip()
        rest_of_line = ','.join(parts[2:])
        
        try:
            # Parse the date (day and month)
            if date_str == "TBD":
                # Keep TBD dates as is
                updated_date = date_str
            else:
                date_parts = date_str.split()
                if len(date_parts) == 2:  # Format: "28 March"
                    day = int(date_parts[0])
                    month_str = date_parts[1]
                    
                    # Convert month name to month number
                    month_names = ["January", "February", "March", "April", "May", "June", 
                                   "July", "August", "September", "October", "November", "December"]
                    month = month_names.index(month_str) + 1
                    
                    # Create date with current year to check if it's past
                    date_with_current_year = datetime(current_year, month, day)
                    
                    # Determine which year to use
                    if date_with_current_year < today:
                        # Date has passed this year, use next year
                        year_to_use = next_year
                    else:
                        # Date is still in the future this year
                        year_to_use = current_year
                    
                    # Create new date string with year
                    updated_date = f"{day} {month_str} {year_to_use}"
                else:
                    # Unexpected format, keep as is
                    updated_date = date_str
        except (ValueError, IndexError):
            # Error in parsing, keep original
            updated_date = date_str
        
        # Reconstruct the line
        updated_line = f"{league}, {updated_date}, {rest_of_line}"
        updated_lines.append(updated_line)
    
    # Write updated content to temp file
    with open(temp_file, 'w', encoding='utf-8') as outfile:
        outfile.writelines(updated_lines)
    
    # Replace original with temp
    os.replace(temp_file, file_path)
    
    print(f"Updated {len(updated_lines)} lines in {file_path}")

if __name__ == "__main__":
    path = r"C:\Users\Eyalp\Desktop\Bundes\backend\data\allgames.txt"
    fix_dates(path)
    print("Date fixing completed successfully!")