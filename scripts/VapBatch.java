import com.tencent.qgame.playerproj.animtool.AnimTool;
import com.tencent.qgame.playerproj.animtool.CommonArg;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public class VapBatch {
    public static void main(String[] args) throws Exception {
        if (args.length < 8) {
            System.err.println("Usage: VapBatch <framesDir> <copyOutDir> <fps> <bitrate> <scale> <ffmpegCmd> <mp4editCmd> <timeoutMinutes>");
            System.exit(1);
        }

        String framesDir = args[0];
        String copyOutDir = args[1];
        int fps = Integer.parseInt(args[2]);
        int bitrate = Integer.parseInt(args[3]);
        float scale = Float.parseFloat(args[4]);
        String ffmpegCmd = args[5];
        String mp4editCmd = args[6];
        long timeoutMinutes = Long.parseLong(args[7]);

        CommonArg arg = new CommonArg();
        arg.ffmpegCmd = ffmpegCmd;
        arg.mp4editCmd = mp4editCmd;
        arg.enableH265 = false;
        arg.fps = fps;
        arg.inputPath = framesDir;
        arg.scale = scale;
        arg.enableCrf = false;
        arg.bitrate = bitrate;
        arg.version = 2;
        arg.needAudio = false;
        arg.isVapx = false;

        File outDir = new File(copyOutDir);
        if (!outDir.exists() && !outDir.mkdirs()) {
            throw new RuntimeException("Failed to create output dir: " + outDir.getAbsolutePath());
        }

        CountDownLatch done = new CountDownLatch(1);
        final boolean[] ok = new boolean[] { false };

        AnimTool tool = new AnimTool();
        tool.setToolListener(new AnimTool.IToolListener() {
            @Override
            public void onProgress(float p) {
                int pct = Math.max(0, Math.min(100, (int) (p * 100.0f)));
                System.out.println("Progress: " + pct + "%");
            }

            @Override
            public void onWarning(String msg) {
                System.out.println("Warning: " + msg);
            }

            @Override
            public void onError() {
                System.err.println("Error: generation failed");
                ok[0] = false;
                done.countDown();
            }

            @Override
            public void onComplete() {
                System.out.println("Generation complete.");
                ok[0] = true;
                done.countDown();
            }
        });

        tool.create(arg, true);

        if (!done.await(timeoutMinutes, TimeUnit.MINUTES)) {
            throw new RuntimeException("Timeout waiting for generation to finish");
        }
        if (!ok[0]) {
            throw new RuntimeException("Generation failed");
        }

        File srcDir = new File(framesDir, "output");
        String[] files = {"video.mp4", "vapc.json", "md5.txt"};
        for (String f : files) {
            File src = new File(srcDir, f);
            if (!src.exists()) {
                throw new RuntimeException("Missing expected output file: " + src.getAbsolutePath());
            }
            Files.copy(src.toPath(), new File(outDir, f).toPath(), StandardCopyOption.REPLACE_EXISTING);
        }
    }
}
