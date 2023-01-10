Param(
    [parameter(mandatory = $true)][String]$template,
    [parameter(mandatory = $true)][String]$stackname,
    [parameter(mandatory = $true)][String]$profile,
    [String[]]$overrides,
    [switch]$force,
    [switch]$new
)
$OutputEncoding = [System.Text.Encoding]::UTF8

# s3 bucket & prefix
$bucketname = "iss-tko-$profile-work-bucket"
$bucketprefix = "cloudformation/manual"

function logger.info($message) {
    Write-Host "INFO: $message" -foregroundcolor cyan
}

function logger.err($message) {
    Write-Host "ERROR: $message" -foregroundcolor red
}

function abort($message) {
    logger.err $message
    exit 1
}

function executable($cmd) {
    Get-Command $cmd -ea SilentlyContinue
    if ($? -eq $true) {
        return $true
    }
    else {
        # コマンドが存在しなければ
        return $false
    }
}

# MFA認証チェック関数
function check_auth() {
    aws cloudformation --profile ${profile} list-stacks 1>$null
    if (-Not $?) {
        abort "MFAの認証が失敗しました"
    }
}

# チェンジセットの作成関数
function deploy_check($template, $stackname, $overrides) {
    $overridesOption = "Dummy=Dummy"
    $overridesStr = $overrides -join " "
    $overridesStr = $overridesStr.trim()
    if ($overridesStr.Length -gt 1) {
        $overridesOption = $overrides
    }

    $result = aws cloudformation --profile ${profile} deploy --template-file ${template} `
        --stack-name ${stackname} `
        --s3-bucket $bucketname `
        --s3-prefix $bucketprefix `
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM `
        --no-fail-on-empty-changeset `
        --no-execute-changeset `
        --parameter-overrides $overridesOption

    if (-Not $?) {
        abort "チェンジセットの取得に失敗しました"
    }

    if ($result | Select-String "No changes to deploy") {
        logger.info "Stackテンプレートに変更がありませんでした"
        exit 0
    }

    $cmd = $result | Select-String -Pattern "^aws cloudformation"
    $cmd = "$cmd --profile ${profile}"
    logger.info "Stackテンプレートのチェンジセットが出力されました"
    # 変更の表示
    $resultJson = Invoke-Expression $cmd | ConvertFrom-Json
    $resultJson.Changes.ResourceChange | Format-Table -Property Action, Replacement, LogicalResourceId, PhysicalResourceId
    if (-Not $? -or $resultJson.Length -eq 0) {
        abort "チェンジセットの取得に失敗しました"
    }
}

# デプロイ関数
function deploy($template, $stackname, $overrides) {
    $overridesOption = "Dummy=Dummy"
    $overridesStr = $overrides -join " "
    $overridesStr = $overridesStr.trim()
    if ($overridesStr.Length -gt 1) {
        $overridesOption = $overrides
    }

    # Stackのデプロイ
    aws cloudformation --profile $profile deploy --template-file $template `
        --stack-name $stackname `
        --s3-bucket $bucketname `
        --s3-prefix $bucketprefix `
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM `
        --no-fail-on-empty-changeset `
        --parameter-overrides $overridesOption

    # Stackのデプロイに失敗した場合、失敗理由を表示して終了する
    if (-Not $?) {
        $resultJson = aws cloudformation --profile ${profile} describe-stack-events --stack-name $stackname | `
            ConvertFrom-Json
        $resultJson.StackEvents | `
            Where-Object { $_.ResourceStatus -Like "*FAILED" -or $_.ResourceStatus -Like "ROLLBACK" } | `
            Select-Object Timestamp, ResourceType, LogicalResourceId, ResourceStatusReason -First 10
        abort "Stackテンプレートのデプロイに失敗しました"
    }
}

# テンプレート取得関数
function getTemplate($stackname) {
    aws cloudformation --profile $profile get-template `
        --stack-name $stackname `
        --output text `
        --query "TemplateBody"
}

function cleanComment($src, $dest) {
    Get-Content $src | `
        ForEach-Object { $_ -replace "^#.*", ""} | `
        ForEach-Object { if($_ -match ".*'.*#.*'.*") { $_ } else { $_.split("#")[0] } } | `
        ForEach-Object { $_ -replace "\s*$", "" } | `
        Where-Object { $_.trim() -ne "" } `
    | Out-File $dest -Encoding Default -Append
}

function diffStack($src, $dest) {
    &"C:\software\WinMerge\WinMergeU.exe" /x `
        $src `
        $dest
}

# awsコマンドの有効性確認
if (-Not(executable "aws")) {
    abort "require [aws] command"
}

# テンプレートの存在確認
if (-Not(Test-Path $template)) {
    abort "${template}を読み込みませんでした"
}

logger.info "AWS Clientの認証状態を確認しています"
check_auth

$trailpath = ".\diffstack\${stackname}\$(Get-Date -Format "yyyyMMdd-HHmmss")"
mkdir $trailpath 1>$null

if (-Not $new) {
    logger.info "Stackテンプレートの保存をしています"
    getTemplate $stackname > $trailpath\current.yml
    if ( -Not (Get-Item $trailpath\current.yml).length -gt 0kb) {
        abort "Stackテンプレート[ $stackname ]の取得に失敗しました"
    }

}

logger.info "Stackテンプレートの文字コードを変換しています"
Get-Content -Path $template -Encoding UTF8 | Out-File ${trailpath}\local.yml -Encoding ascii
cleanComment $trailpath\local.yml ${trailpath}\local-clean.yml
$template = "${trailpath}\local.yml"

if (-Not $new) {
    if (-Not $force) {
        # 改行とコメントを削除
        cleanComment $trailpath\current.yml ${trailpath}\current-clean.yml

        # Stackテンプレートの比較
        logger.info "Stackテンプレートの比較を開始します"
        diffStack $trailpath\current-clean.yml ${trailpath}\local-clean.yml
    }
}

if (-Not $force) {
    # 適用の確認
    $yes = New-Object Management.Automation.Host.ChoiceDescription "&Yes", "はい"
    $no = New-Object Management.Automation.Host.ChoiceDescription "&No", "いいえ"
    $choice = [Management.Automation.Host.ChoiceDescription[]]($yes, $no)
    $answer = $host.UI.PromptForChoice("チェンジセットの作成開始", "チェンジセットの作成を開始しますか？", $choice, 0)

    if ($answer -ne 0) {
        logger.info "チェンジセットの作成がキャンセルされました"
        exit 0
    }
}

logger.info "Stackテンプレートのチェンジセットを確認します"
deploy_check $template $stackname $overrides

if (-Not $force) {
    # 適用の確認
    $yes = New-Object Management.Automation.Host.ChoiceDescription "&Yes", "はい"
    $no = New-Object Management.Automation.Host.ChoiceDescription "&No", "いいえ"
    $choice = [Management.Automation.Host.ChoiceDescription[]]($yes, $no)
    $answer = $host.UI.PromptForChoice("チェンジセットの適用", "これらのチェンジセットを適用しますか？", $choice, 0)

    if ($answer -ne 0) {
        logger.info "チェンジセットの適用がキャンセルされました"
        exit 0
    }
}

logger.info "Stackテンプレートのデプロイを開始します"
deploy $template $stackname $overrides
logger.info "Stackテンプレートのデプロイに成功しました"

exit 0
