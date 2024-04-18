function RequestControl(entity)
  while not NetworkHasControlOfEntity(entity) do
    NetworkRequestControlOfEntity(entity)
    Wait(100)
  end
end

function DeleteExistEntity(entity)
  if not DoesEntityExist(entity) then return end
  DeleteEntity(entity)
end

function LoadGameData(name,waiter)
	local model = (type(name) == "string") and joaat(name) or name
	if IsModelValid(model) then
		if not HasModelLoaded(model) then
			RequestModel(model)
			while waiter and not HasModelLoaded(model) do
				Wait(0)
			end
		end
		return
	end
	if DoesAnimDictExist(name) then
		if not HasAnimDictLoaded(name) then
			RequestAnimDict(name)
			while waiter and not HasAnimDictLoaded(name) do
				Wait(0)
			end
		end
    return
	end
	if DoesStreamedTextureDictExist(name) then
		if not HasStreamedTextureDictLoaded(name) then
			RequestStreamedTextureDict(name, true)
			while waiter and not HasStreamedTextureDictLoaded(name) do
				Wait(0)
			end
		end
		return
	end
end

function ReleaseGameData(name)
	local model = (type(name) == "string") and joaat(name) or name
	if IsModelValid(model) then
		if HasModelLoaded(model) then
			SetModelAsNoLongerNeeded(model)
		end
		return
	end
	if DoesStreamedTextureDictExist(name) then
		if HasStreamedTextureDictLoaded(name) then
		end
		return
	end
	if DoesAnimDictExist(name) then
		if not HasAnimDictLoaded(name) then
			if HasAnimDictLoaded(name) then
				RemoveAnimDict(name)
			end
		end
	end
end