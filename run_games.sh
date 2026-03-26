#!/bin/bash
for i in 000 001 002; do
  echo "Starting game $i..."
  caffeinate -i env RANDOMIZE_ASSIGNMENTS=true python run_llm_game.py --game-id 20260323_bedrock_mix_gunboat_$i --visualize --gun-boat
  echo "Game $i complete."
done
echo "All games finished."
