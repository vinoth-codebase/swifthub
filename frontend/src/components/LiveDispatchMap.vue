<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import L from 'leaflet'

const props = defineProps({
  store: { type: Object, default: null },
  order: { type: Object, default: null },
  riders: { type: Array, default: () => [] },
  heightClass: { type: String, default: 'h-72' },
})

const mapContainer = ref(null)
let map = null
let layerGroup = null
let didFitBounds = false

function makeBadgeIcon(label, bgHex, borderHex = '#FFFFFF') {
  return L.divIcon({
    className: 'swifthub-map-pin',
    html: `<div style="display:inline-flex;align-items:center;justify-content:center;padding:3px 8px;border-radius:9999px;background:${bgHex};color:#FFFFFF;border:2px solid ${borderHex};font-size:11px;font-weight:700;white-space:nowrap;box-shadow:0 2px 6px rgba(15,23,42,0.28);">${label}</div>`,
    iconSize: [0, 0],
    iconAnchor: [24, 14],
  })
}

function renderLayers() {
  if (!map || !layerGroup) return
  layerGroup.clearLayers()

  const points = []

  if (props.store) {
    const hubLatLng = [props.store.lat, props.store.lng]
    points.push(hubLatLng)
    L.marker(hubLatLng, {
      icon: makeBadgeIcon('HUB', '#5B21B6'),
    })
      .bindPopup(`<strong>${props.store.name}</strong><br/>Dark-Store Dispatch Hub`)
      .addTo(layerGroup)
  }

  if (props.order) {
    const custLatLng = [props.order.delivery_lat, props.order.delivery_lng]
    points.push(custLatLng)
    L.marker(custLatLng, {
      icon: makeBadgeIcon('DROP', '#059669'),
    })
      .bindPopup(`<strong>${props.order.customer_name}</strong><br/>Order #ORD-${props.order.id}`)
      .addTo(layerGroup)

    if (props.store) {
      L.polyline(
        [
          [props.store.lat, props.store.lng],
          custLatLng,
        ],
        {
          color: '#7C3AED',
          weight: 3,
          opacity: 0.65,
          dashArray: '6, 8',
        }
      ).addTo(layerGroup)
    }

    if (props.order.rider_id) {
      const assigned = props.riders.find((r) => r.id === props.order.rider_id)
      const riderLat = assigned ? assigned.current_lat : props.order.rider_lat
      const riderLng = assigned ? assigned.current_lng : props.order.rider_lng
      const riderName = assigned ? assigned.name : props.order.rider_name
      const riderStatus = assigned ? assigned.status : props.order.rider_status || 'ASSIGNED'
      if (riderLat != null && riderLng != null && riderName) {
        const riderLatLng = [riderLat, riderLng]
        points.push(riderLatLng)
        L.marker(riderLatLng, {
          icon: makeBadgeIcon(`RIDER: ${riderName.split(' ')[0]}`, '#D97706'),
        })
          .bindPopup(`<strong>${riderName}</strong><br/>Status: ${riderStatus}`)
          .addTo(layerGroup)
      }
    }
  } else if (props.riders && props.riders.length > 0) {
    // Fleet overview mode: show all riders for the store
    props.riders.forEach((rider) => {
      const riderLatLng = [rider.current_lat, rider.current_lng]
      points.push(riderLatLng)
      const bg =
        rider.status === 'DELIVERING'
          ? '#6D28D9'
          : rider.status === 'ASSIGNED'
            ? '#D97706'
            : '#475569'
      L.marker(riderLatLng, {
        icon: makeBadgeIcon(rider.name.split(' ')[0], bg),
      })
        .bindPopup(`<strong>${rider.name}</strong><br/>Status: ${rider.status}`)
        .addTo(layerGroup)
    })
  }

  if (points.length > 1 && !didFitBounds) {
    map.fitBounds(points, { padding: [36, 36], maxZoom: 15 })
    didFitBounds = true
  } else if (points.length === 1 && !didFitBounds) {
    map.setView(points[0], 14)
    didFitBounds = true
  }
}

onMounted(() => {
  if (!mapContainer.value) return
  const center = props.store ? [props.store.lat, props.store.lng] : [12.9352, 77.6245]
  map = L.map(mapContainer.value, {
    center,
    zoom: 14,
    zoomControl: true,
  })

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map)

  layerGroup = L.layerGroup().addTo(map)
  renderLayers()
})

watch(
  () => [props.store?.id, props.order?.id],
  () => {
    didFitBounds = false
    renderLayers()
  }
)

watch(
  () => [props.order, props.riders, props.store],
  () => {
    renderLayers()
  },
  { deep: true }
)

onUnmounted(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="relative rounded-xl overflow-hidden border border-[#E9E5F5] bg-[#FAF8FF]">
    <div ref="mapContainer" class="w-full" :class="heightClass" />
    <div class="absolute bottom-2.5 left-2.5 z-[400] bg-white/95 backdrop-blur-sm border border-[#E9E5F5] rounded-lg px-2.5 py-1.5 flex items-center gap-3 text-[11px] font-medium text-[#475569] shadow-sm">
      <span class="inline-flex items-center gap-1">
        <span class="w-2.5 h-2.5 rounded-full bg-[#5B21B6]" />
        Hub
      </span>
      <span v-if="order" class="inline-flex items-center gap-1">
        <span class="w-2.5 h-2.5 rounded-full bg-[#059669]" />
        Customer Pin
      </span>
      <span class="inline-flex items-center gap-1">
        <span class="w-2.5 h-2.5 rounded-full bg-[#D97706]" />
        Rider GPS
      </span>
    </div>
  </div>
</template>
