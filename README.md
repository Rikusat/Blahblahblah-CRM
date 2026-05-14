# Blahblahblah-CRM

Googleスプレッドシートをデータベースとして使う、軽量CRMアプリです。  
Streamlit Cloud で動作します。

## 機能

- 顧客一覧表示（キーワード検索・業種フィルタ）
- 顧客編集・削除
- 新規登録
- 簡易ダッシュボード（総件数・業種別グラフ）
- スプレッドシートの列追加に自動対応（コード変更不要）

## セットアップ

### 1. 依存関係インストール

```bash
pip install -r requirements.txt
```

### 2. Google Cloud 設定

1. Google Cloud Console でサービスアカウントを作成
2. スプレッドシートAPIとドライブAPIを有効化
3. サービスアカウントのJSONキーを取得
4. 対象のスプレッドシートをサービスアカウントのメールアドレスと共有

### 3. secrets.toml を設定

`.streamlit/secrets.toml` を編集して実際の認証情報を入力してください。

```toml
[gcp_service_account]
type = "service_account"
# ... (サービスアカウントJSONの内容)

[app]
password = "your_password"

[sheets]
spreadsheet_name = "営業リスト"
worksheet_name = "Sheet1"
```

> **注意:** `secrets.toml` は `.gitignore` に含まれています。Gitにコミットしないでください。

### 4. 起動

```bash
streamlit run app.py
```

### Streamlit Cloud へのデプロイ

Streamlit Cloud のダッシュボードで `Secrets` に `secrets.toml` の内容をそのまま貼り付けてください。

## フォルダ構成

```
Blahblahblah-CRM/
├── .streamlit/
│   └── secrets.toml        ← 認証情報（Git管理外）
├── docs/
│   ├── prompts/
│   │   └── claude_crm_mvp_prompt.md
│   ├── specifications/
│   └── architecture/
├── app.py                  ← メイン画面
├── sheets.py               ← Google Sheets操作
├── auth.py                 ← パスワード認証
├── requirements.txt
└── README.md
```
