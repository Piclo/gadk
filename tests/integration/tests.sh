#!/usr/bin/env bash

#
# Hacky integration test script.
#
# TODO: Rewrite in Python.
#

set -euo pipefail

# Make filenames specific to Python version. This way the output of tox tests is separated.
python_version=$(python --version | tail -c +8)
actual_filename="actual-${python_version}.yml"
errors_filename="errors-${python_version}.log"

passed=0

for test_scenario in tests/integration/examples/*
do
  cd "${test_scenario}"

  # Confirm that there are no errors.
  if gadk --print > "${actual_filename}"
  then
    echo "No errors in ${test_scenario}"
  else
    echo "Errors printed for ${test_scenario}"
    cat "${errors_filename}"
    passed=1
    cd - > /dev/null
    continue
  fi

  # Confirm that actual.yml is not empty.
  if ! [[ -s "${actual_filename}" ]]
  then
    echo "${test_scenario} seems to be WIP!"
    passed=1
    cd - > /dev/null
    continue
  else
    # Confirm that actual.yml matches expected.yml.
    if diff -U3 expected.yml "${actual_filename}"
    then
      echo "${test_scenario} has passed!"
    else
      echo "${test_scenario} does not match expected output."
      passed=1
      cd - > /dev/null
      continue
    fi
  fi

  cd - > /dev/null
done

exit "${passed}"
