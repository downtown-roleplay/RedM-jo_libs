-------------
-- INVENTORY
-------------

---@param source integer source ID
---@param item string name of the item
---@param amount integer amount to use
---@param meta table metadata of the item
---@param remove boolean if removed after used
function jo.framework:canUseItem(source, item, amount, meta, remove)
  local count = exports.inventory:GetItem(source, item, meta, true)
  if not count then
    count = 0
  end
  if count >= amount then
    if remove then
      local res = exports.inventory:RemoveItem(source, item, amount, meta)
      return res
    end
  end
  return false
end

---@param item string name of the item
---@param callback function function fired when the item is used
---@param closeAfterUsed boolean if inventory needs to be closes
---@return boolean
function jo.framework:registerUseItem(item, closeAfterUsed, callback)
    exports.core:GetCoreObject().RegisterUsableItem(item, function(source, item)
    local character = exports.core:GetCoreObject().GetCharacterFromPlayerId(source)
    if character then
    if closeAfterUsed then
      character.triggerEvent('ox_inventory:closeInventory')
      end

      callback(source, item)
    end
  end)
end

---@param source integer source ID
---@param item string name of the item
---@param quantity integer quantity
---@param meta table metadata of the item
---@return boolean
function jo.framework:giveItem(source, item, quantity, meta)
  if exports.inventory:CanCarryItem(source, item, quantity, meta) then
    local res = exports.inventory:AddItem(source, item, quantity, meta)
    return res
  end
  return false
end

---@param invName string unique ID of the inventory
---@param name string name of the inventory
---@param invConfig table Configuration of the inventory
---@return boolean
function jo.framework:createInventory(invName, name, invConfig)
  local inventoryConfig = {
    id = invName,
    name = name,
    slots = invConfig.maxSlots,
    maxWeight = invConfig.maxWeight * 1000,
  }
  inventories[invName] = inventoryConfig
  exports.inventory:RegisterStash(inventoryConfig.id, inventoryConfig.name, inventoryConfig.slots, inventoryConfig.maxWeight)
  return true
end

---@param invName string unique ID of the inventory
---@return boolean
function jo.framework:removeInventory(invName)
  return exports.inventory:RemoveInventory(invName)
end

---@param source integer sourceIdentifier
---@param invName string name of the inventory
---@return boolean
function jo.framework:openInventory(source, invName)
  TriggerClientEvent("ox_inventory:openInventory", source, "stash", { id = invName })
  return true
end

---@param invId string unique ID of the inventory
---@param item string name of the item
---@param quantity integer quantity
---@param metadata table metadata of the item
---@param needWait? boolean wait after the adding
---@return boolean
function jo.framework:addItemInInventory(source, invId, item, quantity, metadata, needWait)
  return exports.inventory:AddItem(invId, item, quantity, metadata)
end

---@param invId string name of the inventory
---@return table
function jo.framework:getItemsFromInventory(invId)
  return exports.inventory:GetInventoryItems(invId)
end

-------------
-- END INVENTORY
-------------