#!/usr/bin/env bash

rm -rf migrations/*
rm -rf instance/*

uv run flask --app app db init
uv run flask --app app db migrate -m "initial"
uv run flask --app app db upgrade

uv run flask --app app add-admin-user --username admin --password admin123 --role superadmin
