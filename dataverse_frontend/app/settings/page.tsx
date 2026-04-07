'use client'

import { useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { Bell, Lock, Palette, Save, FileJson, Toggle2, ChevronRight } from 'lucide-react'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general')
  const [settings, setSettings] = useState({
    theme: 'auto',
    notifications: true,
    autoSave: true,
    defaultFormat: 'html',
    maxUploadSize: 50,
    apiVersion: 'v1',
    dataRetention: 30,
  })

  const tabs = [
    { id: 'general', label: 'General', icon: '⚙️' },
    { id: 'privacy', label: 'Privacy & Security', icon: '🔒' },
    { id: 'appearance', label: 'Appearance', icon: '🎨' },
    { id: 'notifications', label: 'Notifications', icon: '🔔' },
    { id: 'api', label: 'API Settings', icon: '⚡' },
  ]

  const handleSave = () => {
    // Save settings to backend
    console.log('Saving settings:', settings)
  }

  return (
    <AppShell>
      <div className="flex h-screen">
        {/* Settings Sidebar */}
        <div className="w-64 border-r border-dv-border bg-dv-bg-secondary p-4">
          <h2 className="font-semibold text-dv-text mb-6">Settings</h2>
          <nav className="space-y-2">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium ${
                  activeTab === tab.id
                    ? 'bg-dv-accent text-white'
                    : 'text-dv-text-secondary hover:text-dv-text hover:bg-dv-bg'
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Settings Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-2xl">
            <h1 className="text-3xl font-bold text-dv-text mb-8">Settings</h1>

            {/* General Settings */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-dv-text mb-4">General Settings</h3>
                  
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-lg border border-dv-border bg-dv-bg">
                      <div>
                        <p className="font-medium text-dv-text">Auto-Save Sessions</p>
                        <p className="text-sm text-dv-text-secondary">Automatically save your analysis progress</p>
                      </div>
                      <Toggle2 className="text-dv-accent" size={20} />
                    </div>

                    <div className="flex items-center justify-between p-4 rounded-lg border border-dv-border bg-dv-bg">
                      <div>
                        <p className="font-medium text-dv-text">Auto-Analysis</p>
                        <p className="text-sm text-dv-text-secondary">Automatically run EDA on dataset upload</p>
                      </div>
                      <Toggle2 className="text-dv-accent" size={20} />
                    </div>

                    <div className="p-4 rounded-lg border border-dv-border bg-dv-bg">
                      <label className="block text-sm font-medium text-dv-text mb-2">
                        Max Upload Size (MB)
                      </label>
                      <input
                        type="number"
                        value={settings.maxUploadSize}
                        onChange={(e) => setSettings({...settings, maxUploadSize: parseInt(e.target.value)})}
                        className="w-full px-3 py-2 rounded border border-dv-border bg-dv-bg-secondary text-dv-text focus:border-dv-accent focus:outline-none"
                      />
                    </div>

                    <div className="p-4 rounded-lg border border-dv-border bg-dv-bg">
                      <label className="block text-sm font-medium text-dv-text mb-2">
                        Default Export Format
                      </label>
                      <select
                        value={settings.defaultFormat}
                        onChange={(e) => setSettings({...settings, defaultFormat: e.target.value})}
                        className="w-full px-3 py-2 rounded border border-dv-border bg-dv-bg-secondary text-dv-text focus:border-dv-accent focus:outline-none"
                      >
                        <option>HTML</option>
                        <option>PDF</option>
                        <option>Excel</option>
                        <option>JSON</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Privacy & Security */}
            {activeTab === 'privacy' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-dv-text">Privacy & Security</h3>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border border-dv-border bg-dv-bg">
                    <div>
                      <p className="font-medium text-dv-text">Data Retention Period</p>
                      <p className="text-sm text-dv-text-secondary">Delete old sessions after N days</p>
                    </div>
                    <select
                      value={settings.dataRetention}
                      onChange={(e) => setSettings({...settings, dataRetention: parseInt(e.target.value)})}
                      className="px-3 py-2 rounded border border-dv-border bg-dv-bg-secondary text-dv-text focus:border-dv-accent focus:outline-none"
                    >
                      <option>7</option>
                      <option>30</option>
                      <option>90</option>
                      <option>365</option>
                    </select>
                  </div>

                  <div className="p-4 rounded-lg border border-dv-border bg-red-50 dark:bg-red-900/20">
                    <p className="font-medium text-red-700 dark:text-red-300 mb-2">Danger Zone</p>
                    <button className="px-4 py-2 rounded border border-red-300 text-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors text-sm font-medium">
                      Delete All Data
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Appearance */}
            {activeTab === 'appearance' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-dv-text">Appearance</h3>
                
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border border-dv-border bg-dv-bg">
                    <label className="block text-sm font-medium text-dv-text mb-4">Theme</label>
                    <div className="space-y-2">
                      {['auto', 'light', 'dark'].map(theme => (
                        <label key={theme} className="flex items-center gap-3 p-2 rounded hover:bg-dv-bg-secondary cursor-pointer">
                          <input
                            type="radio"
                            name="theme"
                            value={theme}
                            checked={settings.theme === theme}
                            onChange={(e) => setSettings({...settings, theme: e.target.value})}
                            className="w-4 h-4"
                          />
                          <span className="capitalize text-dv-text">{theme}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Notifications */}
            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-dv-text">Notifications</h3>
                
                <div className="space-y-4">
                  {['Analysis Complete', 'Model Training Done', 'Export Ready', 'Error Alerts'].map(notif => (
                    <div key={notif} className="flex items-center justify-between p-4 rounded-lg border border-dv-border bg-dv-bg">
                      <p className="text-dv-text">{notif}</p>
                      <Toggle2 className="text-dv-accent" size={20} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* API Settings */}
            {activeTab === 'api' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-dv-text">API Configuration</h3>
                
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border border-dv-border bg-dv-bg">
                    <label className="block text-sm font-medium text-dv-text mb-2">API Version</label>
                    <select
                      value={settings.apiVersion}
                      onChange={(e) => setSettings({...settings, apiVersion: e.target.value})}
                      className="w-full px-3 py-2 rounded border border-dv-border bg-dv-bg-secondary text-dv-text focus:border-dv-accent focus:outline-none"
                    >
                      <option>v1</option>
                      <option>v2</option>
                    </select>
                  </div>

                  <div className="p-4 rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-900/20">
                    <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
                      <strong>API Endpoint:</strong> https://api.dataverse-ai.com/{settings.apiVersion}
                    </p>
                    <button className="text-sm font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1">
                      View Documentation <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Save Button */}
            <div className="flex gap-4 mt-8 pt-6 border-t border-dv-border">
              <button
                onClick={handleSave}
                className="flex items-center gap-2 px-6 py-2 bg-dv-accent text-white rounded-lg font-medium hover:bg-dv-accent-hover transition-colors"
              >
                <Save size={18} />
                Save Changes
              </button>
              <button className="px-6 py-2 border border-dv-border text-dv-text rounded-lg font-medium hover:bg-dv-bg-secondary transition-colors">
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
