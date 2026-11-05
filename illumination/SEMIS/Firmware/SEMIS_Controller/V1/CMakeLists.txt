# The following five lines of boilerplate have to be in your project's
# CMakeLists in this exact order for cmake to work correctly
cmake_minimum_required(VERSION 3.16)

# Must be set before project(V1), since that call processes every component's
# CMakeLists.txt (including html_helper's target_compile_definitions) immediately.
# Values come from secrets.env (KEY=VALUE per line); environment variables
# INFLUX_TOKEN / INFLUX_URL override it if set. secrets.env is registered as a
# configure dependency so editing it triggers a CMake re-run on the next build.
set(INFLUX_TOKEN "")
set(INFLUX_URL "")
set(SECRETS_FILE "${CMAKE_CURRENT_LIST_DIR}/secrets.env")
if(EXISTS "${SECRETS_FILE}")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${SECRETS_FILE}")
    file(STRINGS "${SECRETS_FILE}" _secret_lines)
    foreach(_line IN LISTS _secret_lines)
        string(STRIP "${_line}" _line)
        if(_line MATCHES "^(INFLUX_TOKEN|INFLUX_URL)=(.*)$")
            set(${CMAKE_MATCH_1} "${CMAKE_MATCH_2}")
        endif()
    endforeach()
else()
    message(WARNING "secrets.env not found - InfluxDB upload will be disabled")
endif()
if(DEFINED ENV{INFLUX_TOKEN} AND NOT "$ENV{INFLUX_TOKEN}" STREQUAL "")
    set(INFLUX_TOKEN "$ENV{INFLUX_TOKEN}")
endif()
if(DEFINED ENV{INFLUX_URL} AND NOT "$ENV{INFLUX_URL}" STREQUAL "")
    set(INFLUX_URL "$ENV{INFLUX_URL}")
endif()

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
# "Trim" the build. Include the minimal set of components, main, and anything it depends on.
idf_build_set_property(MINIMAL_BUILD ON)
project(V1)