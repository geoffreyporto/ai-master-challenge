from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import HistGradientBoostingClassifier

BASE = Path('/home/ubuntu/upload')
accounts = pd.read_csv(BASE / 'ravenstack_accounts.csv', parse_dates=['signup_date'])
subs = pd.read_csv(BASE / 'ravenstack_subscriptions.csv', parse_dates=['start_date', 'end_date'])
usage = pd.read_csv(BASE / 'ravenstack_feature_usage.csv', parse_dates=['usage_date']).drop_duplicates('usage_id')
tickets = pd.read_csv(BASE / 'ravenstack_support_tickets.csv', parse_dates=['submitted_at', 'closed_at'])
churn = pd.read_csv(BASE / 'ravenstack_churn_events.csv', parse_dates=['churn_date'])

def b2i(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().eq('true').astype(int)

for col in ['is_trial', 'upgrade_flag', 'downgrade_flag', 'auto_renew_flag']:
    subs[col] = b2i(subs[col])
usage['is_beta_feature'] = b2i(usage['is_beta_feature'])
tickets['escalation_flag'] = b2i(tickets['escalation_flag'])
churn['is_reactivation'] = b2i(churn['is_reactivation'])

# Multiple monthly snapshots allow a prospective, time-aware screening exercise.
# The last two months are untouched for final validation.
snapshot_dates = pd.date_range('2023-04-30', '2024-10-31', freq='ME')
window = pd.Timedelta(days=90)
horizon = pd.Timedelta(days=30)
frames = []
for t0 in snapshot_dates:
    active = subs.loc[(subs['start_date'] <= t0) & (subs['end_date'].isna() | (subs['end_date'] >= t0))].copy()
    if active.empty:
        continue
    # Current commercial state by account as observed at cutoff.
    commercial = active.groupby('account_id').agg(
        active_mrr=('mrr_amount', 'sum'),
        active_seats=('seats', 'sum'),
        active_subscriptions=('subscription_id', 'nunique'),
        annual_share=('billing_frequency', lambda s: (s == 'annual').mean()),
        auto_renew_share=('auto_renew_flag', 'mean'),
        upgrade_share=('upgrade_flag', 'mean'),
        downgrade_share=('downgrade_flag', 'mean'),
    ).reset_index()
    # Usage: left/right half of strict lookback supports trend calculation.
    u = usage.loc[(usage['usage_date'] > t0 - window) & (usage['usage_date'] <= t0)].merge(
        active[['subscription_id', 'account_id']], on='subscription_id', how='inner'
    )
    if not u.empty:
        mid = t0 - pd.Timedelta(days=45)
        usage_agg = u.groupby('account_id').agg(
            usage_total_90d=('usage_count', 'sum'),
            usage_duration_90d=('usage_duration_secs', 'sum'),
            usage_error_total_90d=('error_count', 'sum'),
            feature_breadth_90d=('feature_name', 'nunique'),
            beta_usage_share_90d=('is_beta_feature', 'mean'),
            last_usage_date=('usage_date', 'max'),
        ).reset_index()
        first = u.loc[u['usage_date'] <= mid].groupby('account_id')['usage_count'].sum()
        second = u.loc[u['usage_date'] > mid].groupby('account_id')['usage_count'].sum()
        trend = pd.concat([first.rename('first_half_usage'), second.rename('second_half_usage')], axis=1).fillna(0).reset_index()
        trend['usage_trend_ratio_90d'] = (trend['second_half_usage'] + 1) / (trend['first_half_usage'] + 1)
        usage_agg = usage_agg.merge(trend[['account_id', 'usage_trend_ratio_90d']], on='account_id', how='left')
        usage_agg['days_since_last_usage'] = (t0 - usage_agg['last_usage_date']).dt.days
        usage_agg['errors_per_100_uses_90d'] = 100 * usage_agg['usage_error_total_90d'] / usage_agg['usage_total_90d'].clip(lower=1)
        usage_agg = usage_agg.drop(columns='last_usage_date')
    else:
        usage_agg = pd.DataFrame(columns=['account_id'])
    # Ticket aggregates, all with timestamps no later than cutoff.
    t = tickets.loc[(tickets['submitted_at'] > t0 - window) & (tickets['submitted_at'] <= t0)]
    if not t.empty:
        ticket_agg = t.groupby('account_id').agg(
            tickets_90d=('ticket_id', 'nunique'),
            escalation_rate_90d=('escalation_flag', 'mean'),
            resolution_time_mean_90d=('resolution_time_hours', 'mean'),
            response_time_p90_90d=('first_response_time_minutes', lambda s: s.quantile(.90)),
            high_priority_ticket_share_90d=('priority', lambda s: s.isin(['high', 'urgent']).mean()),
            satisfaction_mean_90d=('satisfaction_score', 'mean'),
            satisfaction_missing_share_90d=('satisfaction_score', lambda s: s.isna().mean()),
        ).reset_index()
    else:
        ticket_agg = pd.DataFrame(columns=['account_id'])
    # Event label: non-reactivation churn strictly after cutoff. Event attributes are excluded by design.
    future = churn.loc[(churn['churn_date'] > t0) & (churn['churn_date'] <= t0 + horizon) & (churn['is_reactivation'] == 0)]
    y = future[['account_id']].drop_duplicates().assign(y=1)
    p = accounts[['account_id', 'industry', 'country', 'referral_source', 'plan_tier', 'seats', 'is_trial', 'signup_date']].copy()
    p['tenure_days'] = (t0 - p['signup_date']).dt.days
    p['is_trial'] = b2i(p['is_trial'])
    p['snapshot_date'] = t0
    p = p.drop(columns=['signup_date'])
    p = p.merge(commercial, on='account_id', how='inner').merge(usage_agg, on='account_id', how='left').merge(ticket_agg, on='account_id', how='left').merge(y, on='account_id', how='left')
    p['y'] = p['y'].fillna(0).astype(int)
    frames.append(p)

panel = pd.concat(frames, ignore_index=True)
# Do not use account ID, snapshot time, or post-outcome data as features.
features = [c for c in panel.columns if c not in {'account_id', 'snapshot_date', 'y'}]
train = panel.loc[panel['snapshot_date'] <= pd.Timestamp('2024-08-31')].copy()
test = panel.loc[panel['snapshot_date'] > pd.Timestamp('2024-08-31')].copy()
num = [c for c in features if pd.api.types.is_numeric_dtype(panel[c])]
cat = [c for c in features if c not in num]
pre = ColumnTransformer([
    ('num', Pipeline([('impute', SimpleImputer(strategy='median'))]), num),
    ('cat', Pipeline([('impute', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore'))]), cat),
], remainder='drop')
model = Pipeline([
    ('pre', pre),
    ('model', HistGradientBoostingClassifier(max_depth=3, learning_rate=.05, max_iter=120, l2_regularization=2.0, random_state=42)),
])
model.fit(train[features], train['y'])
pred = model.predict_proba(test[features])[:, 1]
metrics = {
    'train_rows': int(len(train)), 'test_rows': int(len(test)),
    'train_positive_rate': round(float(train.y.mean()), 4), 'test_positive_rate': round(float(test.y.mean()), 4),
    'test_average_precision': round(float(average_precision_score(test.y, pred)), 4),
    'test_roc_auc': round(float(roc_auc_score(test.y, pred)), 4),
}
# Permutation importance at original-feature level on the most recent untouched dates.
perm = permutation_importance(model, test[features], test.y, n_repeats=15, scoring='average_precision', random_state=42, n_jobs=-1)
imp = pd.DataFrame({'feature': features, 'importance_mean_drop_AP': perm.importances_mean, 'importance_std': perm.importances_std}).sort_values('importance_mean_drop_AP', ascending=False)
# Univariate prospective correlations / incidence differences are descriptive sanity checks only.
univariate = []
for col in num:
    a = train.loc[train.y == 1, col].astype(float)
    b = train.loc[train.y == 0, col].astype(float)
    univariate.append({'feature': col, 'positive_median': round(float(a.median()), 4) if a.notna().any() else None, 'negative_median': round(float(b.median()), 4) if b.notna().any() else None, 'missing_rate': round(float(train[col].isna().mean()), 4)})
report = {
    'screening_design': {
        'unit': 'account_id x monthly snapshot', 'feature_lookback_days': 90, 'label_horizon_days': 30,
        'train_through': '2024-08-31', 'untouched_test': '2024-09-30 to 2024-10-31',
        'warning': 'This is a small-sample feature screen, not a production-performance claim. Permutation importance is predictive, not causal.'
    },
    'metrics': metrics,
    'top_permutation_features': imp.head(25).round(5).to_dict('records'),
    'numeric_descriptives': univariate,
    'feature_columns': features,
}
print(json.dumps(report, indent=2, default=str))
