cmake_minimum_required(VERSION 3.16.0)
include(ExternalProject)
project(opentera-actimetry-service)


if(NOT CMAKE_BUILD_TYPE )
  MESSAGE(STATUS "undefined build type, set to release" )
  set(CMAKE_BUILD_TYPE Release )
elseif(NOT (${CMAKE_BUILD_TYPE} STREQUAL "Release" OR ${CMAKE_BUILD_TYPE} STREQUAL "Debug" ))
  message(FATAL_ERROR "CMAKE_BUILD_TYPE must be either Release or Debug")
endif()

# Make sure venv is installed first
if(NOT PYTHON_ENV_DIRECTORY)
  MESSAGE(STATUS, "Python env directory not specified, using default : ${CMAKE_CURRENT_SOURCE_DIR}/venv")
  set(PYTHON_ENV_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/venv)
endif()

# Python executables should be installed with the opentera package
if(WIN32)
    set(PYTHON_EXECUTABLE ${PYTHON_ENV_DIRECTORY}/bin/python.exe)
    set(PYTHON_PIP_EXECUTABLE ${PYTHON_ENV_DIRECTORY}/bin/pip.exe)
    set(PYBABEL_EXECUTABLE ${PYTHON_ENV_DIRECTORY}/Scripts/pybabel.exe)
else(WIN32)
    set(PYTHON_EXECUTABLE ${PYTHON_ENV_DIRECTORY}/bin/python)
    set(PYTHON_PIP_EXECUTABLE ${PYTHON_ENV_DIRECTORY}/bin/pip)
    # Not sure why, but is installed in .local directory and must be in path
    # You might need to do a symlink in the venv/bin directory...
    set(PYBABEL_EXECUTABLE ${PYTHON_ENV_DIRECTORY}/bin/pybabel)
endif(WIN32)


set (translation_pot_file ${CMAKE_CURRENT_BINARY_DIR}/opentera-actimetry-service.pot)

message(STATUS "PYBABEL EXECUTABLE : ${PYBABEL_EXECUTABLE}")

# Will always be considered out of date...
add_custom_target(
    opentera-actimetry-service-python-translations
    COMMAND ${PYBABEL_EXECUTABLE} extract -F babel.cfg -o ${translation_pot_file} .
    # TO REINITIALIZE TRANSLATION FILES (comment the two lines, or the translations will be overwritten)
    # COMMAND ${PYBABEL_EXECUTABLE} init -i ${translation_pot_file} -d translations -D opentera-actimetry-service -l fr
    # COMMAND ${PYBABEL_EXECUTABLE} init -i ${translation_pot_file} -d translations -D opentera-actimetry-service -l en
    COMMAND ${PYBABEL_EXECUTABLE} update -i ${translation_pot_file} -d translations -D opentera-actimetry-service
    COMMAND ${PYBABEL_EXECUTABLE} compile -d translations -D opentera-actimetry-service
    DEPENDS ${PYBABEL_EXECUTABLE}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/babel.cfg
)

# Will always be considered out of date...
add_custom_target(
    opentera-actimetry-service-python-translations-compile-only
    COMMAND ${PYBABEL_EXECUTABLE} extract -F babel.cfg -o ${translation_pot_file} .
    COMMAND ${PYBABEL_EXECUTABLE} compile -d translations -D opentera-actimetry-service
    DEPENDS ${PYBABEL_EXECUTABLE}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/babel.cfg
)


# Build this target if you want to update translations too...
add_custom_target(opentera-actimetry-service-python-all-with-translations
    DEPENDS opentera-actimetry-service-python-translations)

# Build this target if you want to compile translations only
add_custom_target(opentera-actimetry-service-python-all-with-translations-compile-only ALL
    DEPENDS opentera-actimetry-service-python-translations-compile-only)
