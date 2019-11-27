git push heroku `git subtree split --prefix line_bot master`:master --force

# git subtree split --prefix line_bot master
# git push heroku 5612dd90d7a6d1046026d6db0cb9057d01d7c819:master --force

# heroku psql HEROKU_POSTGRESQL_BROWN_URL
# heroku config:set LD_LIBRARY_PATH=/app/vendor/lib
# app.app_context().push()


# copy to CSV
# heroku psql HEROKU_POSTGRESQL_BROWN_URL
# \copy (SELECT * FROM users) TO users.csv CSV DELIMITER ','
