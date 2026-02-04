RegisterNetEvent("rdr_creator:SkinLoaded")
AddEventHandler("rdr_creator:SkinLoaded", function(skin, ped, clothes)
  ped = ped or PlayerPedId()
  TriggerServerEvent("jo_libs:server:applySkinAndClothes", ped, skin, clothes)
end)

RegisterNetEvent("rdr_creator:ApplyClothes", function(clothes, ped)
  ped = ped or PlayerPedId()
  TriggerServerEvent("jo_libs:server:applyClothes", ped, clothes)
end)

function jo.framework:getInventoryItems()
  return jo.callback.triggerServer("jo_framework_getInventoryItems")
end
