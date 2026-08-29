import OriginalHoloSphere from '../../wu-xing-holo-core-original/src/components/HoloSphere';

type Props = {
  selectedId: string;
  activeDomain?: string;
  onSelect: (id: string) => void;
  focusToken?: number;
};

export default function HoloSphere({ selectedId, activeDomain, onSelect, focusToken }: Props) {
  return <OriginalHoloSphere selectedId={selectedId} activeDomain={activeDomain} onSelect={onSelect} focusToken={focusToken} />;
}
