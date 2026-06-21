#requires -Version 5.1
<#
.SYNOPSIS
    SolidWorks 批量导出 STEP 工具
.DESCRIPTION
    递归扫描 .sldprt / .sldasm 文件，调用本地 SolidWorks COM API 批量导出为 STEP AP214。
    输出目录保持与源目录相同的层级结构。
.NOTES
    - 需要本机安装 SolidWorks
    - 以管理员或普通用户运行均可，但 SolidWorks 会弹出界面
    - 建议导出前关闭其他 SolidWorks 文档
#>

param(
    [string]$SourceDir = "D:\桌面文件\模切机收纸机构",
    [string]$OutputDir = "",
    [string]$FileFilter = "*.sldprt,*.sldasm",
    [int]$TimeoutSeconds = 120
)

# 默认输出目录
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $SourceDir "STEP_Output"
}

$SourceDir = (Resolve-Path $SourceDir).Path
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)

# 创建输出目录
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$LogFile = Join-Path $OutputDir "export_log.txt"
$ErrorLog = Join-Path $OutputDir "export_errors.txt"

function Write-Log($Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Write-ErrorLog($Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $Message"
    Write-Host $line -ForegroundColor Red
    Add-Content -Path $ErrorLog -Value $line -Encoding UTF8
}

# 初始化日志
"SolidWorks 批量 STEP 导出日志" | Set-Content -Path $LogFile -Encoding UTF8
"SolidWorks 批量 STEP 导出错误日志" | Set-Content -Path $ErrorLog -Encoding UTF8

Write-Log "源目录: $SourceDir"
Write-Log "输出目录: $OutputDir"

# 查找所有 SolidWorks 文件
$filters = $FileFilter -split ',' | ForEach-Object { $_.Trim() }
$files = @()
foreach ($filter in $filters) {
    $files += Get-ChildItem -Path $SourceDir -Recurse -Filter $filter -File
}

# 排除输出目录内的文件（防止递归自身）
$files = $files | Where-Object { $_.FullName -notlike "$OutputDir\*" }

Write-Log "找到 $($files.Count) 个 SolidWorks 文件"

if ($files.Count -eq 0) {
    Write-Log "没有找到文件，退出"
    exit 0
}

# 连接 SolidWorks
Write-Log "正在连接 SolidWorks COM..."
$swApp = $null

try {
    # 尝试连接已运行的 SolidWorks 实例
    $swApp = [System.Runtime.InteropServices.Marshal]::GetActiveObject("SldWorks.Application")
    Write-Log "已连接到正在运行的 SolidWorks"
} catch {
    try {
        # 创建新实例
        $swApp = New-Object -ComObject SldWorks.Application
        $swApp.Visible = $true
        Write-Log "已启动新的 SolidWorks 实例"
    } catch {
        Write-ErrorLog "无法连接或启动 SolidWorks: $_"
        exit 1
    }
}

# SolidWorks 文档类型常量
$swDocPART = 1
$swDocASSEMBLY = 2
$swDocDRAWING = 3

# SaveAs 选项
$swSaveAsOptions_Silent = 1
$swSaveAsOptions_Copy = 2
$swSaveAsOptions_SaveReferenced = 4

# 统计
$successCount = 0
$failCount = 0
$skipCount = 0

foreach ($file in $files | Sort-Object FullName) {
    $relativePath = $file.FullName.Substring($SourceDir.Length).TrimStart('\', '/')
    $relativeDir = [System.IO.Path]::GetDirectoryName($relativePath)
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)

    $targetDir = if ([string]::IsNullOrWhiteSpace($relativeDir)) {
        $OutputDir
    } else {
        Join-Path $OutputDir $relativeDir
    }

    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    $outputPath = Join-Path $targetDir "$baseName.step"

    # 如果已存在且文件大小大于 0，跳过
    if (Test-Path $outputPath) {
        $existingSize = (Get-Item $outputPath).Length
        if ($existingSize -gt 1024) {
            Write-Log "[跳过] 已存在: $relativePath"
            $skipCount++
            continue
        }
    }

    Write-Log "[处理] $relativePath"

    $doc = $null
    $errors = 0
    $warnings = 0

    try {
        # 打开文档
        $doc = $swApp.OpenDoc6($file.FullName, $swDocPART, 0, "", [ref]$errors, [ref]$warnings)

        # 如果打开失败，尝试装配体类型
        if ($null -eq $doc) {
            $doc = $swApp.OpenDoc6($file.FullName, $swDocASSEMBLY, 0, "", [ref]$errors, [ref]$warnings)
        }

        if ($null -eq $doc) {
            throw "SolidWorks 无法打开该文件 (errors=$errors, warnings=$warnings)"
        }

        # 导出为 STEP
        # SolidWorks 会根据扩展名 .step 自动选择 STEP 格式
        $saveSuccess = $doc.SaveAs3($outputPath, 0, $swSaveAsOptions_Silent)

        if (-not $saveSuccess) {
            # 尝试 SaveAs4
            $saveSuccess = $doc.SaveAs4($outputPath, 0, $swSaveAsOptions_Silent, [ref]$errors, [ref]$warnings)
        }

        if ($saveSuccess) {
            $outSize = if (Test-Path $outputPath) { (Get-Item $outputPath).Length } else { 0 }
            Write-Log "[成功] $relativePath -> $($outputPath.Replace($OutputDir, 'STEP_Output')) ($([math]::Round($outSize/1KB,2)) KB)"
            $successCount++
        } else {
            throw "SaveAs 返回失败 (errors=$errors, warnings=$warnings)"
        }

    } catch {
        Write-ErrorLog "[失败] $relativePath : $_"
        $failCount++
    } finally {
        # 关闭文档，释放资源
        if ($null -ne $doc) {
            try {
                $swApp.CloseDoc($doc.GetTitle()) | Out-Null
            } catch {
                # 忽略关闭错误
            }
        }
    }

    # 每次导出后短暂停顿，避免 SolidWorks 卡死
    Start-Sleep -Milliseconds 200
}

# 总结
Write-Log "===================================="
Write-Log "处理完成"
Write-Log "成功: $successCount"
Write-Log "跳过: $skipCount"
Write-Log "失败: $failCount"
Write-Log "总计: $($files.Count)"
Write-Log "===================================="

# 可选：退出 SolidWorks（如果脚本启动的实例）
# $swApp.ExitApp()

Write-Host "`n按 Enter 键退出..."
Read-Host
