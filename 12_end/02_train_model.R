#' @name 02_train_model.R
#' @title Train XGBoost Brussels vehicle model; save data/modelr.json
#' @author Tim Fraser
#' @description
#' Builds day_of_week / hour_of_day features from data/traffic.db (metro_id 948),
#' augments with synthetic rows, fits xgboost, prints holdout RMSE, saves model.
#' Run from 12_end/:  Rscript 02_train_model.R

# 0. SETUP ###################################

library(DBI) # for SQLite
library(RSQLite) # for driver
library(xgboost) # for XGBoost
library(jsonlite) # optional helpers

METRO_ID = 948L
OUT_PATH = file.path("data", "modelr.json")
DB_PATH = file.path("data", "traffic.db")

dir.create("data", showWarnings = FALSE, recursive = TRUE)

# 1. LOAD REAL + SYNTHETIC ###################################

rows_from_sqlite = function() {
  if (!file.exists(DB_PATH)) {
    return(data.frame(day_of_week = integer(), hour_of_day = integer(), vehicle_count = numeric()))
  }
  con = dbConnect(RSQLite::SQLite(), DB_PATH)
  on.exit(dbDisconnect(con))
  df = dbGetQuery(
    con,
    "SELECT ingested_at, free_flow_speed, current_speed FROM traffic WHERE metro_id = ?",
    params = list(METRO_ID)
  )
  if (nrow(df) == 0) {
    return(data.frame(day_of_week = integer(), hour_of_day = integer(), vehicle_count = numeric()))
  }
  ts = as.POSIXct(df$ingested_at, tz = "UTC")
  dow = as.integer(strftime(ts, "%u", tz = "UTC")) # 1=Monday … 7=Sunday
  hod = as.integer(strftime(ts, "%H", tz = "UTC"))
  ff = suppressWarnings(as.numeric(df$free_flow_speed))
  cs = suppressWarnings(as.numeric(df$current_speed))
  gap = ifelse(is.na(ff) | is.na(cs), 0, ff - cs)
  set.seed(42)
  noise = rnorm(nrow(df), 0, 45)
  vc = 1000 + 85 * dow + 12.5 * hod + 4.5 * gap + noise
  data.frame(day_of_week = dow, hour_of_day = hod, vehicle_count = vc)
}

synthetic_grid = function(n = 400) {
  set.seed(43)
  dow = sample(1:7, n, replace = TRUE)
  hod = sample(0:23, n, replace = TRUE)
  noise = rnorm(n, 0, 48)
  vc = 1200 + 95 * dow + 14 * hod + noise
  data.frame(day_of_week = dow, hour_of_day = hod, vehicle_count = vc)
}

real = rows_from_sqlite()
syn = synthetic_grid(max(400L, 500L - nrow(real)))
train_df = rbind(real, syn)

# 2. TRAIN ###################################

feat = as.matrix(train_df[, c("day_of_week", "hour_of_day")])
label = train_df$vehicle_count

set.seed(42)
idx = sample(seq_len(nrow(feat)), size = floor(0.8 * nrow(feat)))
x_tr = feat[idx, , drop = FALSE]
y_tr = label[idx]
x_va = feat[-idx, , drop = FALSE]
y_va = label[-idx]

dtrain = xgb.DMatrix(x_tr, label = y_tr)
dval = xgb.DMatrix(x_va, label = y_va)

params = list(
  objective = "reg:squarederror",
  max_depth = 4L,
  eta = 0.08,
  subsample = 0.9,
  seed = 42L
)

bst = xgb.train(params, dtrain, nrounds = 80L, verbose = 0)

pred = predict(bst, dval)
rmse = sqrt(mean((y_va - pred)^2))
message("Model saved to ", OUT_PATH)
message(sprintf("Training RMSE: %.2f", rmse))

xgb.save(bst, OUT_PATH)
message("metro_id=", METRO_ID, " (Brussels); features=day_of_week, hour_of_day")
