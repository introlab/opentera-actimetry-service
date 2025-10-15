message(STATUS "Downloading assets from GitHub...")

# Create data directory if it does not exist
file(MAKE_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/data)
# Set the GitHub access token and asset details
set(GITHUB_ASSET_NAME "2025-06-09_11-54-11-0.zip")
set(ASSET_URL "https://github.com/introlab/opentera-actimetry-service/releases/download/v0.0.0/2025-06-09_11-54-11-0.zip")

set(OUTPUT_FILE "${CMAKE_CURRENT_SOURCE_DIR}/data/${GITHUB_ASSET_NAME}")

file(DOWNLOAD
    "${ASSET_URL}"
    "${OUTPUT_FILE}"
    SHOW_PROGRESS
    TLS_VERIFY ON
    EXPECTED_MD5 "f3c019da074e0aa149b7e2c0345c16a2"
    STATUS download_status
    LOG download_log
)

message(STATUS "Download status: ${download_status}")
message(STATUS "Download log: ${download_log}")

# Unzip the downloaded file
file(ARCHIVE_EXTRACT
    INPUT "${OUTPUT_FILE}"
    DESTINATION "${CMAKE_CURRENT_SOURCE_DIR}/data"
)

message(STATUS "Unzipped data to: ${CMAKE_CURRENT_SOURCE_DIR}/data")
