<?php
/**
 * Szyfromat.pl Integration Config for Nextcloud
 */

$CONFIG = array(
    // Szyfromat.pl Integration
    'szyfromat' => array(
        'enabled' => true,
        'api_url' => getenv('SZYFROMAT_API_URL') ?: 'http://localhost:8500',
        'base_folder' => '/e-Doreczenia',
        'auto_sync' => true,
        'sync_interval' => 300, // seconds
    ),
    
    // Default folders for e-Doręczenia
    'default_folders' => array(
        '/e-Doreczenia',
        '/e-Doreczenia/INBOX',
        '/e-Doreczenia/SENT',
        '/e-Doreczenia/DRAFTS',
        '/e-Doreczenia/ARCHIVE',
        '/e-Doreczenia/TRASH',
    ),
    
    // File naming convention
    'file_naming' => array(
        'pattern' => '{date}/{message_id}/{filename}',
        'date_format' => 'Y-m',
    ),
    
    // Sharing defaults
    'sharing' => array(
        'default_expire_days' => 7,
        'password_required' => false,
        'allow_public_links' => true,
    ),
);
