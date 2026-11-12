<script setup>
import { ref } from 'vue'
import {
  Store,
  ClipboardList,
  Bike,
  BarChart3,
  Zap,
} from 'lucide-vue-next'

const activeTab = ref('storefront')

const tabs = [
  { id: 'storefront', label: 'Customer Storefront', icon: Store },
  { id: 'ops', label: 'Dark-Store Ops', icon: ClipboardList },
  { id: 'riders', label: 'Rider Dispatch', icon: Bike },
  { id: 'analytics', label: 'Ops Analytics', icon: BarChart3 },
]
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#F8FAFC] text-[#0F172A]">
    <header class="sticky top-0 z-30 bg-white border-b border-[#E2E8F0]">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <div class="flex items-center gap-2.5">
          <div class="w-9 h-9 rounded-lg bg-[#1E3A8A] text-white flex items-center justify-center">
            <Zap class="w-5 h-5" />
          </div>
          <div>
            <span class="font-bold text-lg tracking-tight text-[#0F172A]">SwiftHub</span>
            <span class="hidden sm:inline-block ml-2 text-xs font-medium text-[#475569] border-l border-[#E2E8F0] pl-2">
              10-Min Dark-Store Dispatch
            </span>
          </div>
        </div>

        <nav class="flex items-center gap-1 overflow-x-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            @click="activeTab = tab.id"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            :class="
              activeTab === tab.id
                ? 'bg-[#1E3A8A] text-white'
                : 'text-[#475569] hover:bg-slate-100 hover:text-[#0F172A]'
            "
          >
            <component :is="tab.icon" class="w-4 h-4" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>
      </div>
    </header>

    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="bg-white border border-[#E2E8F0] rounded-xl p-8 text-center text-[#475569]">
        Loading SwiftHub operational workspace...
      </div>
    </main>

    <footer class="bg-white border-t border-[#E2E8F0] py-4 mt-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-[#475569]">
        <p>
          SwiftHub is a non-commercial technical portfolio project using simulated operational data.
        </p>
        <p>Bangalore Dark-Store Dispatch Engine</p>
      </div>
    </footer>
  </div>
</template>
