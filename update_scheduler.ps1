# Update the existing TfL_Data_Pipeline task with 3-day repetition
# Requires: Run as Administrator

$taskName = "TfL_Data_Pipeline"

# Get the existing task
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($task) {
    # Export as XML to modify
    $xml = $task | Export-ScheduledTask
    
    # Modify repetition in XML: set to repeat every 10 minutes for 3 days
    $xml = $xml -replace '<Repetition><Interval>PT1M</Interval></Repetition>', '<Repetition><Interval>PT10M</Interval><Duration>P3D</Duration></Repetition>'
    
    # Re-register the task
    $xml | Register-ScheduledTask -TaskName $taskName -Force | Out-Null
    
    Write-Host "[SUCCESS] Task '$taskName' updated successfully!"
    Write-Host "[SUCCESS] Set to run every 10 minutes for 3 days"
    Write-Host "[SUCCESS] After 3 days, collection will stop automatically"
} else {
    Write-Host "[ERROR] Task '$taskName' not found. Run setup_scheduler.ps1 first."
}
