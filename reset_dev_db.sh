#!/usr/bin/env bash

rm -rf instance/*

uv run flask --app app db upgrade

uv run flask --app app add-admin-user --username admin --password admin123 --role superadmin
