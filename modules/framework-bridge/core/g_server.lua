
local function getItemsFromDB()
  return exports.inventory:Items()
end

jo.ready(function()
  Wait(1000)
  jo.framework.inventoryItems = getItemsFromDB()
end)

local function waitInitInventoryItems()
  while table.isEmpty(jo.framework.inventoryItems) do Wait(10) end
end

jo.callback.register.latent("jo_framework_getInventoryItems", function()
  waitInitInventoryItems()
  return jo.framework.inventoryItems
end)

function jo.framework:getInventoryItems()
  waitInitInventoryItems()
  return jo.framework.inventoryItems
end