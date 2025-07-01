#!/usr/bin/env node

/**
 * Build script for Contextly Chrome Extension
 * Prepares the extension for production
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const BUILD_DIR = 'build';
const SRC_DIR = 'src';

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function cleanBuildDir() {
  log('🧹 Cleaning build directory...', colors.yellow);
  if (fs.existsSync(BUILD_DIR)) {
    fs.rmSync(BUILD_DIR, { recursive: true });
  }
  fs.mkdirSync(BUILD_DIR);
}

function copyFiles() {
  log('📁 Copying files...', colors.yellow);
  
  // Files to copy from root
  const rootFiles = ['manifest.json', 'icons'];
  
  // Copy root files
  rootFiles.forEach(file => {
    const src = path.join('.', file);
    const dest = path.join(BUILD_DIR, file);
    
    if (fs.existsSync(src)) {
      if (fs.statSync(src).isDirectory()) {
        fs.cpSync(src, dest, { recursive: true });
      } else {
        fs.copyFileSync(src, dest);
      }
      log(`  ✓ Copied ${file}`);
    }
  });
  
  // Copy extension files
  const extensionDirs = ['background', 'content', 'popup', 'adapters', 'services'];
  
  extensionDirs.forEach(dir => {
    const src = path.join(SRC_DIR, 'extension', dir);
    const dest = path.join(BUILD_DIR, dir);
    
    if (fs.existsSync(src)) {
      fs.cpSync(src, dest, { recursive: true });
      log(`  ✓ Copied ${dir}/`);
    }
  });
  
  // Copy shared modules
  const sharedSrc = path.join(SRC_DIR, 'shared');
  const sharedDest = path.join(BUILD_DIR, 'shared');
  
  if (fs.existsSync(sharedSrc)) {
    fs.cpSync(sharedSrc, sharedDest, { recursive: true });
    log('  ✓ Copied shared modules');
  }
  
  // Fix background script name
  const bgScriptPath = path.join(BUILD_DIR, 'background', 'background.js');
  const oldBgScriptPath = path.join(BUILD_DIR, 'background', 'backround.js');
  
  if (fs.existsSync(oldBgScriptPath) && !fs.existsSync(bgScriptPath)) {
    fs.renameSync(oldBgScriptPath, bgScriptPath);
    log('  ✓ Renamed background script');
  }
}

function updateManifest() {
  log('📝 Updating manifest paths...', colors.yellow);
  
  const manifestPath = path.join(BUILD_DIR, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  
  // Update background script path
  if (manifest.background && manifest.background.service_worker) {
    manifest.background.service_worker = 'background/background.js';
  }
  
  // Update content script paths
  if (manifest.content_scripts) {
    manifest.content_scripts.forEach(script => {
      if (script.js) {
        script.js = script.js.map(js => {
          if (js === 'content.js') return 'content/content.js';
          return js;
        });
      }
    });
  }
  
  // Update popup path
  if (manifest.action && manifest.action.default_popup) {
    manifest.action.default_popup = 'popup/popup.html';
  }
  
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  log('  ✓ Manifest updated');
}

function updatePopupPaths() {
  log('🔗 Updating popup HTML paths...', colors.yellow);
  
  const popupPath = path.join(BUILD_DIR, 'popup', 'popup.html');
  let popupHtml = fs.readFileSync(popupPath, 'utf8');
  
  // Update script paths
  const scriptUpdates = [
    ['walletAdapter.js', '../adapters/walletAdapter.js'],
    ['baseIntegration.js', '../adapters/baseIntegration.js'],
    ['contractService.js', '../services/contractService.js'],
    ['gaslessService.js', '../services/gaslessService.js'],
    ['progressiveOnboarding.js', '../services/progressiveOnboarding.js'],
    ['popup.js', 'popup.js']
  ];
  
  scriptUpdates.forEach(([oldPath, newPath]) => {
    popupHtml = popupHtml.replace(
      `src="${oldPath}"`,
      `src="${newPath}"`
    );
  });
  
  fs.writeFileSync(popupPath, popupHtml);
  log('  ✓ Popup paths updated');
}

function minifyFiles() {
  log('🗜️  Minifying files (optional)...', colors.yellow);
  // Add minification logic here if needed
  log('  ⚠️  Skipping minification (not implemented)');
}

function createPackage() {
  log('📦 Creating extension package...', colors.yellow);
  
  try {
    execSync(`cd ${BUILD_DIR} && zip -r ../contextly-extension.zip .`);
    log('  ✓ Created contextly-extension.zip', colors.green);
  } catch (error) {
    log('  ✗ Failed to create zip file', colors.red);
  }
}

function build() {
  log('\n🚀 Building Contextly Extension\n', colors.bright);
  
  try {
    cleanBuildDir();
    copyFiles();
    updateManifest();
    updatePopupPaths();
    minifyFiles();
    createPackage();
    
    log('\n✅ Build completed successfully!\n', colors.green);
    log(`Extension ready in: ${BUILD_DIR}/`);
    log(`Package created: contextly-extension.zip`);
  } catch (error) {
    log(`\n❌ Build failed: ${error.message}\n`, colors.red);
    process.exit(1);
  }
}

// Run build
build();