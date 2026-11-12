import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'

/**
 * What Wren calls you. Both fields are capped at 80 characters by the API.
 */
export function NameFields({
  address,
  nickname,
  onAddressChange,
  onNicknameChange,
}: {
  address: string
  nickname: string
  onAddressChange: (value: string) => void
  onNicknameChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Label htmlFor="settings-address">What I call you</Label>
        <Input
          id="settings-address"
          name="address"
          maxLength={80}
          value={address}
          onChange={(event) => onAddressChange(event.target.value)}
        />
        <p className="text-xs text-[var(--wren-ink-muted)]">
          {address.trim().length}/80
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="settings-nickname">Nickname</Label>
        <Input
          id="settings-nickname"
          name="nickname"
          maxLength={80}
          value={nickname}
          onChange={(event) => onNicknameChange(event.target.value)}
        />
        <p className="text-xs text-[var(--wren-ink-muted)]">
          {nickname.trim().length}/80
        </p>
      </div>
    </div>
  )
}
