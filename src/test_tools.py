from tools import manage_calendar

# print("--- Testing Calendar Creation ---")
# This test checks if the tool correctly defaults the end_time and works with the API
# result = manage_calendar(
#     action="create", 
#     title="Test Meeting", 
#     start_time="2025-01-20T10:00", 
#     location="Lab"
#     # Note: No end_time provided, the tool should fix this!
# )
# print(result)

print("\n--- Listing Events ---")
print(manage_calendar("list"))