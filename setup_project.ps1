$dirs = @(
"core",
"gui",
"gui\widgets",
"models",
"services",
"services\audio",
"services\tiktok",
"services\tts",
"services\obs",
"services\plugins",
"services\updater",
"assets",
"assets\fonts",
"assets\icons",
"assets\images",
"themes",
"logs",
"sounds",
"tests"
)

foreach($d in $dirs){
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

$files = @(

"README.md",
"LICENSE",
".gitignore",

"core\__init__.py",
"core\app.py",
"core\container.py",
"core\config.py",
"core\constants.py",
"core\event_bus.py",
"core\events.py",
"core\logger.py",

"gui\__init__.py",
"gui\main_window.py",
"gui\sidebar.py",
"gui\chat_panel.py",
"gui\status_bar.py",
"gui\settings_window.py",
"gui\widgets\__init__.py",

"models\__init__.py",
"models\user.py",
"models\comment.py",
"models\gift.py",
"models\follow.py",
"models\like.py",

"services\__init__.py",

"services\audio\__init__.py",
"services\audio\player.py",
"services\audio\cache.py",

"services\tiktok\__init__.py",
"services\tiktok\client.py",
"services\tiktok\filters.py",
"services\tiktok\reconnect.py",

"services\tts\__init__.py",
"services\tts\manager.py",
"services\tts\formatter.py",
"services\tts\queue.py",
"services\tts\voices.py",
"services\tts\edge_engine.py",
"services\tts\sapi_engine.py",
"services\tts\piper_engine.py",

"services\obs\__init__.py",
"services\obs\client.py",

"services\plugins\__init__.py",
"services\plugins\loader.py",

"services\updater\__init__.py",
"services\updater\updater.py",

"tests\test_event_bus.py",
"tests\test_queue.py",
"tests\test_formatter.py",
"tests\test_filters.py"
)

foreach($f in $files){

    if(!(Test-Path $f)){
        New-Item -ItemType File -Path $f | Out-Null
    }

}

Write-Host ""
Write-Host "====================================="
Write-Host " LiveVoice Studio listo"
Write-Host "====================================="