
function getItemsFromDB()
    local awaitItems = promise.new()
    local items = {}

    local tempItems = exports.inventory:Items()

    for _, item in pairs(tempItems) do
        item.image = ("https://cdn.downtownrp.com.br/images/resources/inventory/%s.png"):format(item.name)
        items[item.name] = item;
    end
    
    awaitItems:resolve(items)
    return Await(awaitItems)
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
